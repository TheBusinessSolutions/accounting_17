{
    'name': 'Expense Statement Management',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Quick register for cash and bank expenses',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/expense_statement_views.xml',
        'views/account_journal_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}