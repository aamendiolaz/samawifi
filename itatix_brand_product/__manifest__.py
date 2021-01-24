{
    'name': 'Itatix Brand Product',
    'version': '14.0.0.0',
    'summary': 'Agrega a los reportes de inventario y de analisis de venta la marca, categoria y subcategoria',
    'description': 'Agrega la marca, categoría y subcategoria a diversos reportes y vistas',
    'category': 'All',
    'author': 'ITATIX SA DE CV',
    'website': 'http://itatix.com',
    'license': 'AGPL-3',
    'depends': ['sale', 'product', 'product_unspsc', 'stock_account', 'stock_enterprise'],
    'data': [
        'security/res_groups_sama.xml',
        'security/ir.model.access.csv',
        'views/sama_views.xml',
        'views/product_template_view.xml',
        'views/stock_quant_view.xml',
        'report/sale_report_view.xml'
    ],
    'installable': True,
    'auto_install': False
}
