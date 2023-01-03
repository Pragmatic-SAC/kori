# -*- coding: utf-8 -*-
{
    # App information
    "name": "Pragmatic Kardex - Peru",
    "category": "Reporte de Kardex",
    "summary": "Kardex Pragmatic.",
    "version": "15.0.0",
    "license": "OPL-1",
    "website": "https://www.pragmatic.com.pe/",
    "contributors": [
        "Pragmatic S.A.C <soporte@pragmatic.com.pe>",
    ],
    'depends': ['stock', 'stock_account', 'stock_landed_costs'],
    'data': [
        "security/ir.model.access.csv",
        'security/security.xml',
        'data/states_kardex.xml',
        'views/kardex.xml',
        'views/pragmatic_establishment.xml',
        'views/stock_location.xml',
        'views/stock_warehouse.xml',
    ],
    # Odoo Store Specific
    "images": [

    ],

    # Author
    "author": "Pragmatic S.A.C",
    "website": "pragmatic.com.pe",
    "maintainer": "Pragmatic S.A.C.",

    # Technical
    "installable": True,
    "auto_install": False,
    "application": True,
    "currency": "PEN",
    'assets': {
        'web.assets_backend': [
            'l10n_pe_kardex/static/src/js/action_manager.js',
        ],
    }
}
