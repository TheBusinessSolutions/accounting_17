from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class CashShiftHandover(models.Model):
    _name = 'cash.shift.handover'
    _description = 'Cash Shift Handover'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, readonly=True, default='New')
    
    # Journals
    cash_journal_id = fields.Many2one('account.journal', string='Outbound Journal (Sender)', 
                                      domain=[('type', '=', 'cash')], 
                                      required=True,
                                      default=lambda self: self.env['account.journal'].search([('type', '=', 'cash')], limit=1),
                                      help="The cash journal/box the money is leaving from.")
    
    inbound_journal_id = fields.Many2one('account.journal', string='Inbound Journal (Receiver)', 
                                         domain=[('type', '=', 'cash')],
                                         help="The cash journal/box the money is entering. Leave empty if same as Outbound.")
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='cash_journal_id.currency_id', store=True)

    # Users
    outgoing_user_id = fields.Many2one('res.users', string='Outgoing User', 
                                       default=lambda self: self.env.user, 
                                       required=True, tracking=True)
    incoming_user_id = fields.Many2one('res.users', string='Incoming User', required=True, tracking=True)

    # Amounts
    declared_amount = fields.Monetary(string='Declared Amount', currency_field='currency_id', required=True, tracking=True)
    counted_amount = fields.Monetary(string='Counted Amount', currency_field='currency_id', tracking=True)
    difference = fields.Monetary(string='Difference', compute='_compute_difference', store=True, currency_field='currency_id')

    # Dates & Notes
    outgoing_datetime = fields.Datetime(string='Handover Start', default=fields.Datetime.now)
    received_datetime = fields.Datetime(string='Handover Completed', readonly=True)
    outgoing_notes = fields.Text(string='Outgoing Notes')
    incoming_notes = fields.Text(string='Incoming Notes')
    resolution_notes = fields.Text(string='Resolution Notes')

    # State & Links
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending_validation', 'Pending Validation'),
        ('validated', 'Validated'),
        ('disputed', 'Disputed'),
        ('resolved', 'Resolved')
    ], string='Status', default='draft', tracking=True)

    move_out_id = fields.Many2one('account.move', string='Outgoing Entry', readonly=True, copy=False)
    move_in_id = fields.Many2one('account.move', string='Incoming Entry', readonly=True, copy=False)
    move_resolve_id = fields.Many2one('account.move', string='Resolution Entry', readonly=True, copy=False)

    @api.depends('declared_amount', 'counted_amount')
    def _compute_difference(self):
        for record in self:
            record.difference = (record.counted_amount or 0) - (record.declared_amount or 0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('cash.shift.handover') or 'New'
        return super().create(vals_list)

    def action_submit_handover(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Only draft handovers can be submitted."))
        if not self.declared_amount:
            raise ValidationError(_("Please enter the declared amount."))
        
        self._create_journal_entry('outgoing')
        self.write({'state': 'pending_validation', 'outgoing_datetime': fields.Datetime.now()})
        self.message_post(body=_("Handover submitted by %s.") % self.outgoing_user_id.name)
        return True

    def action_validate_handover(self):
        self.ensure_one()
        if self.state != 'pending_validation':
            raise UserError(_("Handover is not pending validation."))
        if self.incoming_user_id != self.env.user:
            raise UserError(_("Only the assigned incoming user can validate this handover."))
        if not self.counted_amount:
            raise ValidationError(_("Please enter the counted amount."))

        self._create_journal_entry('incoming')
        new_state = 'validated' if self.difference == 0 else 'disputed'
        self.write({'state': new_state, 'received_datetime': fields.Datetime.now()})
        self.message_post(body=_("Handover validated. Status: %s") % new_state)
        return True

    def _get_suspense_account(self):
        suspense_account_id = self.env['ir.config_parameter'].sudo().get_param('cash_shift_handover.suspense_account_id')
        if suspense_account_id:
            account = self.env['account.account'].browse(int(suspense_account_id))
            if account.exists():
                return account
        raise UserError(_("Suspense Account not configured in Accounting Settings."))

    def _create_journal_entry(self, side):
        self.ensure_one()
        journal = self.cash_journal_id if side == 'outgoing' else (self.inbound_journal_id or self.cash_journal_id)
        suspense_account = self._get_suspense_account()
        cash_account = journal.default_account_id
        
        if not cash_account:
            raise UserError(_("Journal '%s' has no default account.") % journal.name)

        amount = self.declared_amount if side == 'outgoing' else self.counted_amount
        
        # Outgoing: Dr Suspense / Cr Cash
        # Incoming: Dr Cash / Cr Suspense
        debit_acc = suspense_account if side == 'outgoing' else cash_account
        credit_acc = cash_account if side == 'outgoing' else suspense_account

        move = self.env['account.move'].create({
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'ref': f"{self.name} - {side.title()}",
            'line_ids': [
                (0, 0, {'account_id': debit_acc.id, 'debit': amount, 'credit': 0, 'name': f"{side.title()} Handover"}),
                (0, 0, {'account_id': credit_acc.id, 'debit': 0, 'credit': amount, 'name': f"{side.title()} Handover"})
            ]
        })
        move.action_post()
        
        if side == 'outgoing':
            self.move_out_id = move.id
        else:
            self.move_in_id = move.id

    # --- Phase 2 & 3: Resolution & Correction Methods ---

    def action_open_resolve_wizard(self):
        self.ensure_one()
        if self.state != 'disputed':
            raise UserError(_("Only disputed handovers can be resolved."))
        return {
            'name': _('Resolve Variance'),
            'type': 'ir.actions.act_window',
            'res_model': 'cash.shift.resolve.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_handover_id': self.id,
                'default_difference': self.difference,
                'default_incoming_user_id': self.incoming_user_id.id,
            }
        }

    def action_resolve_variance(self, resolution_type, account_id, partner_id=None, notes=""):
        self.ensure_one()
        suspense_account = self._get_suspense_account()
        amount = abs(self.difference)
        
        if self.difference < 0: # Shortage
            lines = [
                (0, 0, {'account_id': account_id.id, 'debit': amount, 'credit': 0, 'partner_id': partner_id.id if partner_id else False}),
                (0, 0, {'account_id': suspense_account.id, 'debit': 0, 'credit': amount})
            ]
        else: # Overage
            lines = [
                (0, 0, {'account_id': suspense_account.id, 'debit': amount, 'credit': 0}),
                (0, 0, {'account_id': account_id.id, 'debit': 0, 'credit': amount, 'partner_id': partner_id.id if partner_id else False})
            ]

        move = self.env['account.move'].create({
            'journal_id': self.cash_journal_id.id,
            'date': fields.Date.today(),
            'ref': f"RESOLVE/{self.name}",
            'line_ids': lines
        })
        move.action_post()
        
        # Link the resolution entry
        self.write({'state': 'resolved', 'resolution_notes': notes, 'move_resolve_id': move.id})
        self.message_post(body=_("Variance resolved: %s") % resolution_type)
        return True

    def action_reverse_handover(self):
        """Reverse all accounting entries and reset to Draft for correction"""
        self.ensure_one()
        if self.state not in ['disputed', 'validated']:
            raise UserError(_("Only Validated or Disputed handovers can be reversed for correction."))
        
        # Helper to safely remove moves
        def safe_remove(move):
            if move:
                if move.state == 'posted':
                    move.button_cancel()
                move.with_context(force_delete=True).unlink()

        safe_remove(self.move_resolve_id)
        safe_remove(self.move_in_id)
        safe_remove(self.move_out_id)

        # Reset State and Fields
        self.write({
            'state': 'draft',
            'counted_amount': 0,
            'received_datetime': False,
            'move_out_id': False,
            'move_in_id': False,
            'move_resolve_id': False,
            'resolution_notes': False
        })
        
        self.message_post(body=_("Handover reversed by Manager for correction. Please re-enter counts."))
        return True