# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ApprovalRefuseWizard(models.TransientModel):
    _name = 'approval.refuse.wizard'
    _description = 'Approval Refuse Wizard'

    request_id = fields.Many2one('approval.request', string='Request', required=True)
    comment = fields.Text(string='Reason', required=True)

    def action_refuse(self):
        """Refuse the request with comment"""
        self.ensure_one()
        if not self.request_id:
            raise UserError(_('No request selected.'))
        
        self.request_id.action_refuse(self.comment)
        return {'type': 'ir.actions.act_window_close'}

