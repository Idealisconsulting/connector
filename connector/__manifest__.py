# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013-2014 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{'name': 'Connector',
 'version': '10.0.1.0.0',
 'author': 'Camptocamp,Openerp Connector Core Editors,'
           'Odoo Community Association (OCA)',
 'website': 'http://odoo-connector.com',
 'license': 'AGPL-3',
 'category': 'Generic Modules',
 'depends': ['mail',
             'queue_job',
             ],
 'external_dependencies': {'python': ['requests'
                                      ],
                           },
 'data': ['security/connector_security.xml',
          'security/ir.model.access.csv',
          'checkpoint/checkpoint_view.xml',
          'connector_menu.xml',
          'setting_view.xml',
          'res_partner_view.xml',
          ],
 'installable': True,
 'application': True,
 }
