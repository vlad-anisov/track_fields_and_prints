from odoo import models


class Base(models.AbstractModel):
    _inherit = "base"

    def name_get(self):
        """
        OVERRIDE
        Generates name if 'create_name' in context and default name is False
        """
        result = super().name_get()
        if self.env.context.get("is_create_name"):
            for index, data in enumerate(result):
                record_id = self.browse(data[0])
                data = data[1].split(",")
                if len(data) == 2 and data[0] == record_id._name and data[1] == str(record_id.id):
                    name_elements = []
                    for field_name, field in record_id._fields.items():
                        if field.type not in ("many2many", "one2many", "boolean", "date", "datetime") and field_name not in ("create_date", "write_date", "create_uid", "write_uid", "id"):
                            field_record = getattr(record_id, field_name)
                            if hasattr(field_record, "id"):
                                value = field_record.name_get()[0][1]
                            else:
                                value = field_record
                            if value:
                                name_elements.append(str(value))
                    name = set(", ".join(set(name_elements)).split(", "))
                    result[index] = (record_id.id, ", ".join(name))
        return result