import logging

from bs4 import BeautifulSoup
from werkzeug.urls import url_quote

from odoo import fields, models

_logger = logging.getLogger(__name__)


class MailMail(models.Model):
    _inherit = "mail.mail"

    def send(self, auto_commit=False, raise_exception=False):
        for mail in self:
            if mail.mail_message_id and (mail.email_to or mail.recipient_ids):
                trace = self._create_tracking_trace(mail)
                mail.body_html = self._add_tracking(mail.body_html, trace.id)

        return super().send(auto_commit=auto_commit, raise_exception=raise_exception)

    def _create_tracking_trace(self, mail):
        email = mail.email_to or self._get_first_recipient_email(mail.recipient_ids)
        tracking_data = {
            "mail_message_id": mail.mail_message_id.id
            if mail.mail_message_id
            else False,
            "email": email if email else "",
            "message_id": mail.message_id,
            "status": "tracking_added",
            "sent_at": fields.Datetime.now(),
        }
        return self.env["mailing.trace"].create(tracking_data)

    def _get_first_recipient_email(self, recipient_ids):
        if recipient_ids:
            first_recipient = self.env["res.partner"].browse(recipient_ids.ids[:1])
            return first_recipient.email
        return None

    def _add_tracking(self, body_html, trace_id):
        tracking_pixel = f'<img src="/mail/track/open/{trace_id}" width="1" height="1" style="display:none"/>'

        last_div_index = body_html.rfind("</div>")
        if last_div_index != -1:
            body_html = (
                body_html[:last_div_index] + tracking_pixel + body_html[last_div_index:]
            )

        return self._replace_links_with_tracked(body_html, trace_id)

    def _replace_links_with_tracked(self, body_html, trace_id):
        soup = BeautifulSoup(body_html, "html.parser")

        for a_tag in soup.find_all("a", href=True):
            original_url = a_tag["href"]
            tracked_url = (
                f"/mail/track/click/{trace_id}?redirect_url={url_quote(original_url)}"
            )
            a_tag["href"] = tracked_url

        return str(soup)
