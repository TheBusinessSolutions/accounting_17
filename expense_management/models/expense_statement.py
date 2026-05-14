from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ExpenseStatement(models.Model):
    _name = 'expense.statement'
    _description = 'Expense Statement'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True, readonly=True, states={'draft': [('readonly', False)]})
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, domain=[('type', 'in', ('bank', 'cash'))])
    description = fields.Char(string='Description')
    line_ids = fields.One2many('expense.statement.line', 'statement_id', string='Transactions')
    state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted')], string='Status', default='draft', tracking=True)
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('expense.statement') or _('New')
        return super().create(vals)

    def action_validate(self):
        for record in self:
            if not record.line_ids:
                raise UserError(_("Please add at least one line."))
            
            move_lines = []
            for line in record.line_ids:
                # Logic: Out (Debit Account, Credit Journal) | In (Debit Journal, Credit Account)
                liquidity_acc = record.journal_id.default_account_id.id
                
                # Transaction Line
                move_lines.append((0, 0, {
                    'name': line.note or record.description or record.name,
                    'account_id': line.account_id.id,
                    'debit': line.amount if line.transaction_type == 'out' else 0.0,
                    'credit': line.amount if line.transaction_type == 'in' else 0.0,
                }))
                # Offsetting Liquidity Line
                move_lines.append((0, 0, {
                    'name': line.note or record.description or record.name,
                    'account_id': liquidity_acc,
                    'debit': line.amount if line.transaction_type == 'in' else 0.0,
                    'credit': line.amount if line.transaction_type == 'out' else 0.0,
                }))

            move = self.env['account.move'].create({
                'journal_id': record.journal_id.id,
                'date': record.date,
                'ref': record.name,
                'move_type': 'entry',
                'line_ids': move_lines,
            })
            move.action_post()
            record.write({'move_id': move.id, 'state': 'posted'})

    def action_draft(self):
        for record in self:
            if record.move_id:
                record.move_id.button_draft()
                record.move_id.unlink()
            record.state = 'draft'

class ExpenseStatementLine(models.Model):
    _name = 'expense.statement.line'
    _description = 'Expense Statement Line'

    statement_id = fields.Many2one('expense.statement', ondelete='cascade')
    transaction_type = fields.Selection([('in', 'Input'), ('out', 'Output')], string='Type', default='out', required=True)
    account_id = fields.Many2one('account.account', string='Account', required=True)
    amount = fields.Float(string='Amount', required=True)
    note = fields.Char(string='Note')