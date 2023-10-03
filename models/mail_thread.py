from odoo import models, api, tools, _
from odoo.tools import html2plaintext

SUBJECT = _("Changes in Fields")

ARROW_HTML = """
    <span class="fa fa-long-arrow-right">
    </span>
"""

ADD = _("Added")
DELETE = _("Deleted")

MANY_INFO = {
    0: _("Created New Line"),
    1: _("Updated Line"),
    2: _("Removed Line"),
    3: _("Removed Line"),
    6: _("many2many"),
}


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @tools.ormcache("self.env.uid", "self.env.su")
    def _get_tracked_fields(self):
        """
        Adds all fields for track, if field is_track_all_fields is True
        """
        if self.env["ir.model"].sudo().search([("model", "=", str(self._name))], limit=1).is_track_all_fields:
            fields = {name for name, field in self._fields.items() if name not in ["write_date", "__last_update"]}
        else:
            fields = {
                name
                for name, field in self._fields.items()
                if getattr(field, "tracking", None)
                or getattr(field, "track_visibility", None)
                or self.env["ir.model"].sudo().search([("model", "=", str(self._name))], limit=1).is_track_all_fields
            }

        return fields and set(self.fields_get(fields))

    @api.model
    def get_last_value(self, id_of_record, model=None, field=None, field_type=None):
        """
        Returns last value.
        """
        field = id_of_record and field or []
        record_id = self.env[model].browse(id_of_record)
        if "many2one" in field_type:
            value = field and record_id[field] and record_id[field].with_context(is_create_name=True).name_get() or ""
            value = value and value[0][1]
        elif "many2many" in field_type:
            value = record_id[field].ids
        else:
            value = field and record_id[field] or ""
        return field and value or ""

    @api.model
    def prepare_many_info(self, records, string, model, last=None, is_before_write=True):
        """
        Return message for x2many field.
        """
        obj = self.env[model]
        rec_name = obj._rec_name
        message = ""
        mes = ""
        last = last or []
        for val in records:
            if not val or not MANY_INFO.get(val[0]):
                continue
            if is_before_write:
                if val[0] in (2, 3):
                    doc = obj.browse(val[1])
                    last_value = doc.with_context(is_create_name=True).name_get()[0][1]
                    message = f"""
                        {message}\n
                        <li>{MANY_INFO.get(val[0])}: {last_value}</li>
                    """
                elif val[0] == 6:
                    last_values = list(set(val[2]) - set(last))
                    new = list(set(last) - set(val[2]))
                    if last_values and not new:
                        adds = [obj.browse(i).with_context(is_create_name=True).name_get()[0][1] for i in last_values]
                        mes = " - ".join(adds)
                        message = f"""
                            {message}\n
                            <li>{ADD} {string}: {mes}</li>
                        """
                    if not last_values and new:
                        deletes = [obj.browse(i).with_context(is_create_name=True).name_get()[0][1] for i in new]
                        mes = "-".join(deletes)
                        message = f"""
                            {message}\n
                            <li>{DELETE} {string}: {mes}</li>
                        """
                elif val[0] == 1:
                    values = val[2]
                    line_id = 0
                    for field in values:
                        fields_list = obj._fields
                        if fields_list[field].type in ("one2many", "many2many"):
                            last_value = self.get_last_value(val[1], model, field, "many2many")
                            field_str = self.get_string_by_field(obj, field)
                            relation = fields_list[field].comodel_name
                            mes = self.prepare_many_info(values[field], field_str, relation, last_value)
                        elif fields_list[field].type == "many2one":
                            mes = self.prepare_many2one_info(val[1], model, field, values)
                        elif "many" not in fields_list[field].type:
                            mes = self.prepare_simple_info(val[1], model, field, values)
                        if mes and mes != "<p>":
                            message = (
                                (line_id != val[1])
                                and f"""
                                    {message}\n\n
                                    <p class="mt-4 font-italic">
                                        {_("ID")} {val[1]}:
                                        {obj.browse(val[1]).with_context(is_create_name=True).name_get()[0][1]} 
                                    </p>
                                """
                                or message
                            )
                            message = f"{message}{mes}"
                            line_id = val[1]
            else:
                if val[0] == 0:
                    id_of_new_record = 0
                    ids_before_write = [x[1] for x in records]
                    for index, id_of_last in enumerate(last):
                        if id_of_last not in ids_before_write:
                            id_of_new_record = id_of_last
                            del last[index]
                            break
                    record_id = obj.browse(id_of_new_record)
                    name = record_id.with_context(is_create_name=True).name_get()[0][1]
                    message = f"""
                        {message}\n
                        <li>
                            {MANY_INFO.get(val[0])}: 
                            {name}
                        </li>
                    """
        if message:
            return f"<ul>{message}</ul>"

    @api.model
    def get_selection_value(self, obj, field, value):
        """
        Returns selection value.
        """
        attr = "selection"
        selection = dict(obj.fields_get([field], [attr])[field][attr])
        string = selection.get(value, "")
        return string

    @api.model
    def get_string_by_field(self, obj, field):
        """
        Returns string by field.
        """
        attr = "string"
        description = obj.fields_get([field], [attr])[field][attr]
        return description

    @api.model
    def prepare_many2one_info(self, doc_id, model, field, vals):
        """
        Return message for many2one field.
        """
        obj = self.env[model]
        message = "<p>"
        fields_list = obj._fields
        last_value = self.get_last_value(doc_id, model, field, fields_list[field].type)
        relation_obj = self.env[fields_list[field].comodel_name]
        relation_doc = relation_obj.browse(vals[field])
        new_value = relation_doc.with_context(is_create_name=True).name_get()[0][1] if relation_doc else ""
        if last_value != new_value and any((new_value, last_value)):
            message = f"""
                <li>
                    {self.get_string_by_field(obj, field)}: 
                    {last_value} {ARROW_HTML} {new_value}
                </li>
            """
        return message

    @api.model
    def prepare_simple_info(self, doc_id, model, field, vals):
        """
        Returns message for field.
        """
        obj = self.env[model]
        fields_list = obj._fields
        last_value = self.get_last_value(doc_id, model, field, fields_list[field].type)
        new_value = vals[field]
        if fields_list[field].type == "selection":
            last_value = self.get_selection_value(obj, field, last_value)
            new_value = self.get_selection_value(obj, field, vals[field])
        if last_value == new_value or not all((last_value, vals[field])):
            return "<p>"
        message = (
            f"""
            <li>
                {self.get_string_by_field(obj, field)}: 
                {last_value} {ARROW_HTML} {new_value}
            </li>"""
            or "<p>"
        )
        return message

    def write(self, values):
        """
        Added message about changes fields in chatter.
        """
        for record_id in self.sudo():
            body = ""
            for field_name in values:
                field = self._fields[field_name]
                if field.type in ("one2many", "many2many") and any(
                    [
                        getattr(field, "tracking", None),
                        getattr(field, "track_visibility", None),
                        self.env["ir.model"]
                        .sudo()
                        .search([("model", "=", str(self._name))], limit=1)
                        .is_track_all_fields,
                    ]
                ):
                    last_value = self.get_last_value(record_id.id, self._name, field_name, "many2many")
                    field_str = self.get_string_by_field(self, field_name)
                    message = self.prepare_many_info(values[field_name], field_str, field.comodel_name, last_value, is_before_write=True)
                    if message:
                        body = f"{body}<li>{field_str}: {message}</li>"
            if body and html2plaintext(body):
                record_id.message_post(body=f"<ul>{body}</ul>")
        result = super().write(values)
        for record_id in self.sudo():
            body = ""
            for field_name in values:
                field = self._fields[field_name]
                if field.type in ("one2many", "many2many") and any(
                    [
                        getattr(field, "tracking", None),
                        getattr(field, "track_visibility", None),
                        self.env["ir.model"]
                        .sudo()
                        .search([("model", "=", str(self._name))], limit=1)
                        .is_track_all_fields,
                    ]
                ):
                    last_value = self.get_last_value(record_id.id, self._name, field_name, "many2many")
                    field_str = self.get_string_by_field(self, field_name)
                    message = self.prepare_many_info(values[field_name], field_str, field.comodel_name, last_value, is_before_write=False)
                    if message:
                        body = f"{body}<li>{field_str}: {message}</li>"
            if body and html2plaintext(body):
                record_id.message_post(body=f"<ul>{body}</ul>")
        return result
