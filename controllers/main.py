from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import Action, clean_action


class TrackFieldsAndPrintsAction(Action):

    @http.route('/web/action/load', type='json', auth="user")
    def load(self, action_id, additional_context=None):
        """
        OVERRIDE
        Adds message in chatter when user print report.
        """
        result = super().load(action_id, additional_context)
        if all([
            result.get("binding_type") == "report",
            result.get("type"),
            result.get("name"),
            result.get("id"),
            request.context.get("active_model"),
            request.context.get("active_ids"),
            request.env[result.get("type")].sudo().search([("id", "=", result.get("id"))]).binding_model_id.is_track_all_prints,
        ]):
            for record_id in request.env[request.context.get("active_model")].sudo().search([("id", "in", request.context.get("active_ids"))]):
                record_id.message_post(body=f"{result.get('name')} printed")
        return result
