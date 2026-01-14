# -*- coding: utf-8 -*-

from odoo import models, fields


class ApprovalPaymentMethod(models.Model):
    _name = 'approval.payment.method'
    _description = 'Approval Payment Method'
    _order = 'name'

    name = fields.Char(string='Payment Method', required=True)
    active = fields.Boolean(string='Active', default=True)

