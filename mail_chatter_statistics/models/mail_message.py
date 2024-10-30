from datetime import datetime

from odoo import api, fields, models, tools


class MailMessage(models.Model):
    _inherit = "mail.message"

    mailing_trace_ids = fields.One2many(
        comodel_name="mailing.trace",
        inverse_name="mail_message_id",
        string="Mailing Traces",
        help="Mailing traces related to this message.",
    )

    @api.onchange("parent_id")
    def _onchange_parent_id_update_replied(self):
        """
        Detecta si el mensaje actual es una respuesta (tiene un `parent_id`),
        y actualiza `replied_at` en el `mailing.trace` asociado al mensaje original.
        """
        if self.parent_id:
            mailing_trace = self.env["mailing.trace"].search(
                [("mail_message_id", "=", self.parent_id.id)], limit=1
            )
            if mailing_trace:
                mailing_trace.replied_at = datetime.now()

    def is_bounced(self):
        """
        Verifica si el mensaje ha sido rechazado o rebotado.
        Si es así, actualiza el campo `bounced_at` en `mailing.trace`.
        Retorna True si el mensaje está en estado `exception` en mail.mail.
        """
        mail_mail = self.env["mail.mail"].search(
            [("mail_message_id", "=", self.id), ("state", "=", "exception")], limit=1
        )

        if mail_mail:
            # Buscar el mailing trace correspondiente y actualizar `bounced_at`
            mailing_trace = self.env["mailing.trace"].search(
                [("mail_message_id", "=", self.id)], limit=1
            )
            if mailing_trace:
                mailing_trace.bounced_at = datetime.now()
            return True
        return False

    @api.model
    def message_process_incoming(self, message, message_dict):
        super(MailMessage, self).message_process_incoming(message, message_dict)

        thread_references = message_dict.get("references") or message_dict.get(
            "in_reply_to"
        )
        msg_references = (
            tools.mail_header_msgid_re.findall(thread_references)
            if thread_references
            else []
        )

        if msg_references:
            self.env["mailing.trace"].set_opened(mail_message_ids=msg_references)
            self.env["mailing.trace"].set_replied(mail_message_ids=msg_references)

    @api.model
    def get_mailing_trace(self, mail_message_id):
        if mail_message_id:
            mail_message_id = int(mail_message_id)
        mailing_trace = self.env["mailing.trace"].search(
            [("mail_message_id", "=", mail_message_id)], limit=1
        )

        if mailing_trace:
            return mailing_trace.read(
                [
                    "id",
                    "sent_at",
                    "clicked_at",
                    "opened_at",
                    "bounced_at",
                    "replied_at",
                    "user_agent",
                ]
            )[0]
        return False
