# -*- coding: utf-8 -*-
###############################################################################
#
#   connector-ecommerce for OpenERP
#   Copyright (C) 2013-TODAY Akretion <http://www.akretion.com>.
#     @author Sébastien BEAU <sebastien.beau@akretion.com>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import logging

from openerp.addons.connector.connector import ConnectorUnit
from openerp.addons.connector.unit.backend_adapter import BackendAdapter
from ..backend import prestashop

_logger = logging.getLogger(__name__)


class DirectBinder(ConnectorUnit):
    _model_name = None
    _erp_field = None
    _ps_field = None
    _copy_fields = []

    def _compare_function(ps_val, erp_val, ps_dict, record):
        raise NotImplementedError

    def run(self):
        _logger.debug(
            "[%s] Starting synchro between OERP and PS"
            % self.model._description
        )
        nr_ps_already_mapped = 0
        nr_ps_mapped = 0
        nr_ps_not_mapped = 0
        # Get all OERP obj
        sess = self.session
        erp_model_name = self.model._inherits.iterkeys().next()
        erp_rec_name = sess.pool[erp_model_name]._rec_name
        erp_records = sess.env[erp_model_name].search([])
        adapter = self.unit_for(BackendAdapter)
        # Get the IDS from PS
        ps_ids = adapter.search()
        if not ps_ids:
            raise osv.except_osv(
                _('Error :'),
                _('Failed to query %s via PS webservice')
                % adapter.prestashop_model
            )
        binder = self.binder_for()
        # Loop on all PS IDs
        for ps_id in ps_ids:
            # Check if the PS ID is already mapped to an OE ID
            erp_id = binder.to_openerp(ps_id)
            if erp_id:
                # Do nothing for the PS IDs that are already mapped
                _logger.debug(
                    "[%s] PS ID %s is already mapped to OERP ID %s"
                    % (self.model._name, ps_id, erp_id)
                )
                nr_ps_already_mapped += 1
            else:
                # PS IDs not mapped => I try to match between the PS ID and
                # the OE ID. First, I read field in PS
                ps_dict = adapter.read(ps_id)
                mapping_found = False
                # Loop on OE IDs
                for record in erp_records:
                    # Search for a match
                    erp_val = record[self._erp_field]
                    ps_val = ps_dict[self._ps_field]
                    if self._compare_function(
                            ps_val,
                            erp_val,
                            ps_dict,
                            record):
                        # it matches, so I write the external ID
                        data = {
                            'openerp_id': record['id'],
                            'backend_id': self.backend_record.id,
                        }
                        for oe_field, ps_field in self._copy_fields:
                            data[oe_field] = record[ps_field]
                        ps_erp_id = sess.env[self._model_name].create(data)
                        binder.bind(ps_id, ps_erp_id)
                        _logger.debug(
                            "[%s] Mapping PS '%s' (%s) to OERP '%s' (%s)"
                            % (self.model._name,
                               ps_dict['name'],  # not hardcode if needed
                               ps_dict[self._ps_field],
                               record[erp_rec_name],
                               record[self._erp_field]))
                        nr_ps_mapped += 1
                        mapping_found = True
                        break
                if not mapping_found:
                    # if it doesn't match, I just print a warning
                    _logger.warning(
                            "[%s] PS '%s' (ps id: %s, value: %s) was not mapped to any OERP entry"
                        % (self.model._name,
                           ps_dict['name'],
                           ps_id,
                           ps_dict[self._ps_field]))

                    nr_ps_not_mapped += 1

        _logger.info(
            "[%s] Synchro between OERP and PS successfull"
            % self.model._name
        )
        _logger.info(
            "[%s] Number of PS entries already mapped = %s"
            % (self.model._name, nr_ps_already_mapped)
        )
        _logger.info(
            "[%s] Number of PS entries mapped = %s"
            % (self.model._name, nr_ps_mapped)
        )
        _logger.info(
            "[%s] Number of PS entries not mapped = %s"
            % (self.model._name, nr_ps_not_mapped)
        )

        return True


@prestashop
class CarrierDirectBinder(DirectBinder):
    _model_name = 'prestashop.delivery.carrier'
    _erp_field = 'name'
    _ps_field = 'name_ext'

    #def _compare_function(self, ps_val, erp_val, ps_dict, record):
    #    if len(erp_val) >= 2 and len(ps_val) >= 2 and \
    #            erp_val[0:2].lower() == ps_val[0:2].lower():
    #        return True
    #    return False


@prestashop
class LangDirectBinder(DirectBinder):
    _model_name = 'prestashop.res.lang'
    _erp_field = 'code'
    _ps_field = 'language_code'
    _copy_fields = [
        ('active', 'active'),
    ]

    def _compare_function(self, ps_val, erp_val, ps_dict, record):
        if len(erp_val) >= 2 and len(ps_val) >= 2 and \
                erp_val[0:2].lower() == ps_val[0:2].lower():
            return True
        return False


@prestashop
class CountryDirectBinder(DirectBinder):
    _model_name = 'prestashop.res.country'
    _erp_field = 'code'
    _ps_field = 'iso_code'

    def _compare_function(self, ps_val, erp_val, ps_dict, record):
        if len(erp_val) >= 2 and len(ps_val) >= 2 and \
                erp_val[0:2].lower() == ps_val[0:2].lower():
            return True
        return False


@prestashop
class ResCurrencyDirectBinder(DirectBinder):
    _model_name = 'prestashop.res.currency'
    _erp_field = 'name'
    _ps_field = 'iso_code'

    def _compare_function(self, ps_val, erp_val, ps_dict, record):
        if len(erp_val) == 3 and len(ps_val) == 3 and \
                erp_val[0:3].lower() == ps_val[0:3].lower():
            return True
        return False


@prestashop
class AccountTaxDirectBinder(DirectBinder):
    _model_name = 'prestashop.account.tax'
    _erp_field = 'amount'
    _ps_field = 'rate'

    def _compare_function(self, ps_val, erp_val, ps_dict, record):
        taxes_inclusion_test = self.backend_record.taxes_included and \
            record['price_include'] or not record['price_include']
        if taxes_inclusion_test and record['type_tax_use'] == 'sale' and \
                abs(erp_val*100 - float(ps_val)) < 0.01 and \
                self.backend_record.company_id.id == record.company_id.id:
            return True
        return False
