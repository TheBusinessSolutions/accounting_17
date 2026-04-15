{
    'name': 'Invoice Partner Balance',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Invoicing',
    'summary': 'Show partner GL balance before and after invoice',
    'description': """
        Displays the partner's General Ledger balance before the invoice,
        and the updated balance after posting. Supports multi-currency & Arabic.
    """,
    'depends': ['account'],
    'data': [
        'views/account_move_views.xml',
        'report/invoice_report_templates.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}