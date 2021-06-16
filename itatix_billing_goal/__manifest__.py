{
    'name': 'Itatix Billing Goal',
    'version': '14.0.0.0.0',
    'summary': 'Desarrollo de metas de facturacion',
    'description': 'Este modulo agrega a las vistas de sales team el manejo en dolares y las metas de facturacion'
                   'en las ventas, y facturas',
    'category': 'Sales',
    'author': 'ITATIX SA DE CV',
    'license': 'AGPL-3',
    'depends': ['crm', 'sale', 'sales_team', 'hr', 'account'],
    'data': [
        'views/res_users_form_view.xml',
        'views/res_partner_form_view.xml',
        'views/hr_employee_form_view.xml',
        'views/sale_order_form_view.xml',
        'views/account_move.xml',
        'views/crm_view.xml',
        'wizard/crm_lead_stage_probability.xml'
    ],
    'installable': True,
}