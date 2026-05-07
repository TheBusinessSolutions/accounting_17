from odoo import models, fields, api

class CashShiftResolveWizard(models.TransientModel):
    _name = 'cash.shift.resolve.wizard'
    _description = 'Cash Shift Variance Resolution Wizard'

    handover_id = fields.Many2one('cash.shift.handover', required=True, readonly=True)
    
    # Add Currency Field
    currency_id = fields.Many2one('res.currency', related='handover_id.currency_id')
    
    # Link Monetary field to Currency
    difference = fields.Monetary(string='Difference', currency_field='currency_id', readonly=True)
    
    incoming_user_id = fields.Many2one('res.users', related='handover_id.incoming_user_id', readonly=True)
    
    resolution_type = fields.Selection([
        ('expense', 'Write-off as Expense (Shortage)'),
        ('income', 'Record as Income (Overage)'),
        ('employee', 'Assign to Employee (Receivable)'),
    ], string='Resolution Type', required=True)
    
    account_id = fields.Many2one('account.account', string='Account', required=True, domain="[('deprecated', '=', False)]")
    partner_id = fields.Many2one('res.partner', string='Employee/Partner')
    notes = fields.Text(string='Notes')

    @api.onchange('resolution_type')
    def _onchange_resolution_type(self):
        if self.resolution_type == 'expense':
            acc = self.env['account.account'].search([('account_type', '=', 'expense'), ('company_id', '=', self.handover_id.company_id.id)], limit=1)
            self.account_id = acc
            self.partner_id = False
        elif self.resolution_type == 'income':
            acc = self.env['account.account'].search([('account_type', '=', 'other_income'), ('company_id', '=', self.handover_id.company_id.id)], limit=1)
            self.account_id = acc
            self.partner_id = False
        elif self.resolution_type == 'employee':
            self.partner_id = self.incoming_user_id.partner_id if self.incoming_user_id else False
            
    def action_resolve(self):
        self.handover_id.action_resolve_variance(
            resolution_type=self.resolution_type,
            account_id=self.account_id,
            partner_id=self.partner_id,
            notes=self.notes
        )
        return {'type': 'ir.actions.act_window_close'}