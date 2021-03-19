{
    'name': 'Amount Invoice Discount',
    'version': '14.0.1.0.0',
    'category': 'Sales Management',
    'summary': "Discount on Total Amount in Invoice",
    'author': 'Techspawn Solutions Pvt. Ltd.',
    'website': 'http://www.techspawn.com',
    'description': """

Discount on Total Amount in Invoice

""",
    'depends': ['sale',
                'account',
                ],
    'data': [
        'views/account_invoice_view.xml',
    ],
}
