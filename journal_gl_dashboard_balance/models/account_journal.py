from odoo import models, fields, api


class AccountJournal(models.Model):
    _inherit = "account.journal"

    company_currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True
    )

    balance = fields.Monetary(
        string="Balance",
        currency_field="company_currency_id",
        compute="_compute_dashboard_data"
    )

    payments_total = fields.Monetary(
        string="Payments",
        currency_field="company_currency_id",
        compute="_compute_dashboard_data"
    )

    misc_total = fields.Monetary(
        string="Misc",
        currency_field="company_currency_id",
        compute="_compute_dashboard_data"
    )

    @api.depends("default_account_id")
    def _compute_dashboard_data(self):
        for journal in self:
            journal.balance = 0.0
            journal.payments_total = 0.0
            journal.misc_total = 0.0

            if not journal.default_account_id:
                continue

            account_id = journal.default_account_id.id
            company_id = journal.company_id.id

            # Payments
            self.env.cr.execute("""
                SELECT COALESCE(SUM(aml.debit - aml.credit), 0)
                FROM account_move_line aml
                JOIN account_move am ON aml.move_id = am.id
                WHERE aml.account_id = %s
                  AND aml.company_id = %s
                  AND am.state = 'posted'
                  AND aml.payment_id IS NOT NULL
            """, (account_id, company_id))
            payments = self.env.cr.fetchone()[0] or 0.0

            # Misc
            self.env.cr.execute("""
                SELECT COALESCE(SUM(aml.debit - aml.credit), 0)
                FROM account_move_line aml
                JOIN account_move am ON aml.move_id = am.id
                WHERE aml.account_id = %s
                  AND aml.company_id = %s
                  AND am.state = 'posted'
                  AND aml.payment_id IS NULL
            """, (account_id, company_id))
            misc = self.env.cr.fetchone()[0] or 0.0

            journal.payments_total = payments
            journal.misc_total = misc
            journal.balance = payments + misc

    def action_open_journal_items(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Journal Items',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': [
                ('account_id', '=', self.default_account_id.id),
                ('move_id.state', '=', 'posted'),
                ('company_id', '=', self.company_id.id),
            ],
        }