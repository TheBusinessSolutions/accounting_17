from odoo import models, fields, api


class AccountJournal(models.Model):
    _inherit = "account.journal"

    company_currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True
    )

    gl_balance = fields.Monetary(
        string="GL Balance",
        currency_field="company_currency_id",
        compute="_compute_balances"
    )

    dashboard_balance = fields.Monetary(
        string="Dashboard Balance",
        currency_field="company_currency_id",
        compute="_compute_balances"
    )

    balance_difference = fields.Monetary(
        string="Difference",
        currency_field="company_currency_id",
        compute="_compute_balances"
    )

    @api.depends("default_account_id")
    def _compute_balances(self):

        journals = self.filtered(lambda j: j.default_account_id)
        results_map = {}

        if journals:
            account_ids = journals.mapped("default_account_id").ids
            company_ids = journals.mapped("company_id").ids
            journal_ids = journals.ids

            query = """
                SELECT 
                    aml.account_id,
                    aml.company_id,
                    aml.journal_id,

                    SUM(aml.debit - aml.credit) AS gl_balance,

                    -- Dashboard-like (only same journal)
                    SUM(CASE 
                        WHEN aml.journal_id = aj.id 
                        THEN (aml.debit - aml.credit)
                        ELSE 0 
                    END) AS dashboard_balance

                FROM account_move_line aml
                JOIN account_move am ON aml.move_id = am.id
                JOIN account_journal aj ON aml.journal_id = aj.id

                WHERE aml.account_id IN %s
                  AND aml.company_id IN %s
                  AND aml.journal_id IN %s
                  AND am.state = 'posted'

                GROUP BY aml.account_id, aml.company_id, aml.journal_id
            """

            self.env.cr.execute(query, (
                tuple(account_ids),
                tuple(company_ids),
                tuple(journal_ids),
            ))

            for account_id, company_id, journal_id, gl, dash in self.env.cr.fetchall():
                results_map[(account_id, company_id, journal_id)] = (gl, dash)

        for journal in self:
            key = (
                journal.default_account_id.id,
                journal.company_id.id,
                journal.id
            )

            gl, dash = results_map.get(key, (0.0, 0.0))

            journal.gl_balance = gl
            journal.dashboard_balance = dash
            journal.balance_difference = gl - dash