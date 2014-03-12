from __future__ import absolute_import

from flask import current_app, get_template_attribute, render_template
from smtplib import SMTP, SMTP_SSL, LMTP
try:
    from email.mime.text import MIMEText
    from urllib.parse import unquote_plus, urlparse
except:
    from email import MIMEText
    from urllib import unquote_plus
    from urlparse import urlparse


def send_mail(from_addr, to, subject, body):
    dest_url = current_app.config['SMTP_URL']

    if not dest_url:
        return

    dest_url = urlparse(dest_url)

    type_handlers = {
        'smtp': SMTP,
        'smtp+ssl': SMTP,
        'smtps': SMTP_SSL,
        'lmtp': LMTP,
    }

    init_args = {}
    if dest_url.hostname:
        init_args['host'] = dest_url.hostname or unquote_plus(dest_url.path)
        if dest_url.port:
            init_args['port'] = int(dest_url.port)

    assert(dest_url.scheme in type_handlers)

    sender = type_handlers[dest_url.scheme](**init_args)

    sender.ehlo_or_helo_if_needed()

    if '+ssl' in dest_url.scheme:
        sender.starttls()
        sender.ehlo()

    if dest_url.username:
        sender.login(
            unquote_plus(dest_url.username),
            unquote_plus(dest_url.password)
        )

    msg = MIMEText(body, _charset='UTF-8')
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to

    sender.sendmail(from_addr, [to], msg.as_string())
    sender.quit()


def send_template(to, template, data):
    if not current_app.config.get('SMTP_FROM'):
        return

    subj = get_template_attribute(template, 'subject')
    body = render_template(template, **data)
    send_mail(current_app.config['SMTP_FROM'], to, subj, body)
