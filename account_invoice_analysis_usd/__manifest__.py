# -*- coding: utf-8 -*-
{
    'name': 'Account Invoice Analysis Report',
    'version': '14.0.1.14.8',
    'category': 'Accounting',
    'author': "QuilSoft",
    'maintainer': 'Luis Aquino - luis.aquino@quilsoft.com',
    'website': 'https://www.quilsoft.com',
    'summary': """Account Invoice Analysis Report""",
    'depends': [
        'base', 
        'account', 
        'account_custom_sama', 
        'itatix_account_extended'
    ],
    'data': [
        'security/ir.model.access.csv',
        'reports/account_invoice_analysis_report_view.xml',
        'views/menuitems.xml',
    ],
    'installable': True,
    'application': True,
    'sequence': 1,
    'auto_install': False,
}
