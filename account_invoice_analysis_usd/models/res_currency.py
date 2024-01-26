# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class ResCurrency(models.Model):
    _inherit = 'res.currency'


    @api.model
    def _get_query_currency_usd_table(self, options):
        ''' Construct the currency table as a mapping company -> rate to convert the amount to the user's company
        currency in a multi-company/multi-currency environment.
        The currency_table is a small postgresql table construct with VALUES.
        :param options: The report options.
        :return:        The query representing the currency table.
        '''

        user_company = self.env.company
        user_currency = user_company.currency_id
        usd_currency = self.env.ref("base.USD")
        if options.get('multi_company', False):
            companies = self.env.companies
            conversion_date = options['date']['date_to']
            currency_rates = companies.mapped('currency_id')._get_rates(user_company, conversion_date)
        else:
            companies = user_company
            currency_rates = {user_currency.id: 1.0}

        _logger.info('*************Currency Rates********************')
        _logger.info(currency_rates)
        conversion_rates = []
        for company in companies:
            _logger.info('*************Currency Rates 2********************')
            _logger.info(currency_rates[user_company.currency_id.id])
            _logger.info('*************Currency Rates 3********************')
            _logger.info(currency_rates[company.currency_id.id])
            _logger.info('*************Currency Rates 4********************')
            _logger.info((1/currency_rates[user_company.currency_id.id]))
            if company.currency_id.id != usd_currency.id:
                conversion_rates.extend((
                company.id,
                (1/currency_rates[company.currency_id.id]),
                user_currency.decimal_places,
            ))
            else:
                conversion_rates.extend((
                    company.id,
                    currency_rates[user_company.currency_id.id] / currency_rates[company.currency_id.id],
                    user_currency.decimal_places,
                ))
        query = '(VALUES %s) AS currency_table(company_id, rate, precision)' % ','.join('(%s, %s, %s)' for i in companies)
        return self.env.cr.mogrify(query, conversion_rates).decode(self.env.cr.connection.encoding)

ResCurrency()