from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cash_shift_suspense_account_id = fields.Many2one(
        'account.account', 
        string='Cash Shift Suspense Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        config_parameter='cash_shift_handover.suspense_account_id',
        help="Account used to hold temporary differences during cash shift handovers."
    )