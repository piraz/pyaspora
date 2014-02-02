import codecs
import html
import json
from flask import url_for

renderers = {}


def renderer(formats):
    def stash_format(f):
        for fmt in formats:
            renderers[fmt] = f
        return f
    return stash_format


@renderer(['text/plain'])
def text_plain(part, fmt, url):
    if part.inline and fmt == 'text/html':
        return '<pre>{}</pre>'.format(html.escape(part.mime_part.text_preview))
    return None


@renderer(['text/html'])
def text_html(part, fmt, url):
    if part.inline and fmt == 'text/html':
        return codecs.utf_8_decode(part.body)[0]
    return None


@renderer(['image/jpeg', 'image/gif', 'image/png'])
def common_images(part, fmt, url):
    if fmt == 'text/html' and part.inline:
        return '<img src="{}" alt="{}" />'.format(
            url_for('content.raw', id=part.mime_part.id, _external=True),
            part.mime_part.text_preview
        )


@renderer(['application/x-pyaspora-subscribe'])
def pyaspora_subscribe(part, fmt, url):
    from pyaspora.contact.models import Contact
    if fmt != 'text/html' or not part.inline:
        return

    payload = json.loads(part.mime_part.body.decode('utf-8'))
    from_contact = Contact.get(payload['from'])
    to_contact = Contact.get(payload['to'])
    return '<a href="{}">{}</a> subscribed to <a href="{}">{}</a>'.format(
        url_for('contacts.profile',
                contact_id=from_contact.id, _external=True),
        html.escape(from_contact.realname),
        url_for('contacts.profile', contact_id=to_contact.id, _external=True),
        html.escape(to_contact.realname),
    )


def render(part, fmt, url=None):
    if not url:
        url = url_for('content.raw', part_id=part.mime_part.id)

    ret = None
    if part.mime_part.type in renderers:
        ret = renderers[part.mime_part.type](part, fmt, url)

    if ret is not None:  # might be empty string!
        return ret

    defaults = {
        'text/html': {
            True: lambda p: html.escape(p.mime_part.text_preview),
            False: lambda p: '<a href="{}">(link)</a>'.format(url)
        },
        'text/plain': {
            True: lambda p: p.mime_part.text_preview,
            False: lambda p: 'Link: {}'.format(url)
        }
    }

    if fmt in defaults:
        return defaults[fmt][part.inline](part)

    return None
