{
    'name': 'Cash Shift Handover',
    'version': '17.0.2.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Manage cash safe handovers with multi-journal support and variance resolution.',
    'description': """
        Cash Shift Handover Management
        ==============================
        * Support for Single Box Rotation and Inter-Branch Transfers.
        * Configurable Suspense Account via Settings.
        * Manager Resolution Wizard for Disputes.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': ['account', 'mail'],
    'data': [
        'security/cash_shift_security.xml',
        'security/ir.model.access.csv',
        'views/cash_shift_views.xml',
        'views/menu.xml',
        'views/res_config_settings_views.xml',
        'wizard/resolve_variance_views.xml',
        'data/sequence.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}