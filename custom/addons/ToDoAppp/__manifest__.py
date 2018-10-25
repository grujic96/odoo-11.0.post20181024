# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'To-Do Application',
    'author': 'Aleksandar',
    'depends': ['base'],
    'application': True,
    'description': """
This is the base module for managing products and pricelists in Odoo.
========================================================================

Products support variants, different pricing methods, vendors information,
make to stock/order, different units of measure, packaging and properties.

Pricelists support:
-------------------
    * Multiple-level of discount (by product, category, quantities)
    * Compute price based on different criteria:
        * Other pricelist
        * Cost price
        * List price
        * Vendor price

Pricelists preferences by product and/or partners.

Print product labels with barcode.
    """,
    'data': [
        #'report/product_template_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}
