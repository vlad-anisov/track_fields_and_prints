from odoo import models, fields


class IrModel(models.Model):
    _inherit = 'ir.model'

    is_track_all_fields = fields.Boolean(string="Track all fields")
    is_track_all_prints = fields.Boolean(string="Track all prints")
