from odoo import api, fields, models

class AccountMove(models.Model):
    _inherit = 'account.move'

    partner_balance_before = fields.Monetary(
        string="Partner Balance Before",
        currency_field='company_currency_id',
        readonly=True,
        store=True,
        help="Current GL balance of the partner excluding this invoice."
    )
    partner_balance_after = fields.Monetary(
        string="Partner Balance After",
        currency_field='company_currency_id',
        readonly=True,
        store=True,
        help="Projected GL balance after this invoice is posted."
    )

    def action_refresh_balances(self):
        """Manually refresh partner balances on demand to save performance."""
        for move in self:
            if not move.partner_id or move.move_type not in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
                move.write({'partner_balance_before': 0.0, 'partner_balance_after': 0.0})
                continue

            commercial_partner = move.partner_id.commercial_partner_id
            domain = [
                ('partner_id.commercial_partner_id', '=', commercial_partner.id),
                ('parent_state', '=', 'posted'),
                ('account_id.account_type', 'in', ['asset_receivable', 'liability_payable']),
                ('move_id', '!=', move.id),
            ]
            lines = self.env['account.move.line'].sudo().search_read(domain, ['balance'])
            balance_before = sum(line.get('balance', 0.0) for line in lines)

            move_date = move.date or fields.Date.today()
            company = move.company_id or self.env.company
            amount_total_company = move.amount_total
            
            if move.currency_id and move.company_currency_id and move.currency_id != move.company_currency_id:
                amount_total_company = move.currency_id._convert(
                    move.amount_total, move.company_currency_id, company, move_date
                )

            move.write({
                'partner_balance_before': balance_before,
                'partner_balance_after': balance_before + amount_total_company,
            })
        return True