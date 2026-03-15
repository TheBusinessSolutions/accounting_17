# -*- coding: utf-8 -*-

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
        compute="_compute_gl_balance",
        help="Current balance of the journal default account"
    )

    def action_open_gl_account(self):
        self.ensure_one()

        return {
            "name": "GL Report",
            "type": "ir.actions.act_window",
            "res_model": "account.move.line",
            "view_mode": "tree,form",
            "domain": [
                ("account_id", "=", self.default_account_id.id),
                ("parent_state", "=", "posted"),
                ("company_id", "=", self.company_id.id),
            ],
            "context": {
                "create": False
            },
        }

    @api.depends("default_account_id")
    def _compute_gl_balance(self):

        journals = self.filtered(lambda j: j.default_account_id)
        balances = {}

        if journals:

            account_ids = journals.mapped("default_account_id").ids
            company_ids = journals.mapped("company_id").ids

            query = """
                SELECT account_id, company_id, SUM(debit - credit) AS balance
                FROM account_move_line
                WHERE account_id IN %s
                AND company_id IN %s
                AND parent_state = 'posted'
                GROUP BY account_id, company_id
            """

            self.env.cr.execute(query, (tuple(account_ids), tuple(company_ids)))
            results = self.env.cr.fetchall()

            for account_id, company_id, balance in results:
                balances[(account_id, company_id)] = balance

        for journal in self:
            key = (journal.default_account_id.id, journal.company_id.id)
            journal.gl_balance = balances.get(key, 0.0)