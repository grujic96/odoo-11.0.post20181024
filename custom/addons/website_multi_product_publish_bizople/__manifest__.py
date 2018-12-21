# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Bizople Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Multi Product Publish/Unpublish',
    'category': 'Website',
    'version': '11.0.1.0.0',
    'author': 'Bizople Solutions Pvt. Ltd.',
    'website': 'https://www.bizople.com',
    'summary': 'Multi Product Publish and Unpublish',
    'description': """Multi Product Publish and Unpublish""",
    'depends': [
        'product',
        'website_sale',
    ],
    'data': [
        'wizard/product_publish_view.xml',
        'views/product_publish.xml',
    ],
     'images': [
        'static/description/banner.png'
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'AGPL-3',
}
