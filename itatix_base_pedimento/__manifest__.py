{
    "name": "Modulo base para propagacion de pedimento agrupador",
    "author": "ITATIX SA DE CV, ",
    "version": "14.0.0.0.0",
    "category": "Inventory",
    "depends": ["stock", "stock_landed_costs", "sale", "sale_stock", "account"],
    "data": [
        "views/stock_picking_view.xml",
        "views/account_move_view.xml",
        "report/report_invoice.xml"
    ],
    "license": "AGPL-3",
    "installable": True,
}
