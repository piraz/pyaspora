import codecs
import json
from flask import render_template_string, url_for

renderers = {}


def renderer(formats):
    """
    Decorator which remembers the functions and the MIME types that they
    will render.
    """
    def stash_format(f):
        for fmt in formats:
            renderers[fmt] = f
        return f
    return stash_format


def renderer_exists(fmt):
    """
    Returns true if there's a renderer for
    specific formats.
    """
    return renderers.get(fmt, None)


@renderer(['text/plain'])
def text_plain(part, fmt, url):
    """
    Renderer for text/plain.
    """
    if part.inline:
        if fmt == 'text/html':
            return render_template_string(
                '{{text|nl2br}}',
                text=codecs.utf_8_decode(part.mime_part.body)[0]
            )
        if fmt == 'text/plain':
            return codecs.utf_8_decode(part.mime_part.body)[0]
    return None


@renderer(['text/html'])
def text_html(part, fmt, url):
    """
    Renderer for text/html.
    """
    if part.inline and fmt == 'text/html':
        return codecs.utf_8_decode(part.mime_part.body)[0]
    return None


@renderer(['image/jpeg', 'image/gif', 'image/png'])
def common_images(part, fmt, url):
    """
    Renderer for image/* that a browser can display in an <img> tag.
    """
    if fmt == 'text/html' and part.inline:
        return render_template_string(
            '<img src="{{url}}" alt="{{alt}}" />',
            url=url_for('content.raw',
                        part_id=part.mime_part.id, _external=True),
            alt=part.mime_part.text_preview
        )


@renderer(['application/x-pyaspora-subscribe'])
def pyaspora_subscribe(part, fmt, url):
    """
    Standard message for when a contact subscribes to you.
    """
    from pyaspora.contact.models import Contact
    if fmt != 'text/html' or not part.inline:
        return

    payload = json.loads(part.mime_part.body.decode('utf-8'))
    to_contact = Contact.get(payload['to'])
    return render_template_string(
        'subscribed to <a href="{{profile}}">{{name}}</a>',
        profile=url_for('contacts.profile',
                        contact_id=to_contact.id, _external=True),
        name=to_contact.realname
    )


@renderer(['application/x-pyaspora-share'])
def pyaspora_share(part, fmt, url):
    """
    Standard message for when a post is shared.
    """
    if fmt != 'text/html' or not part.inline:
        return

    payload = json.loads(part.mime_part.body.decode('utf-8'))
    author = payload['author']
    return render_template_string(
        "shared <a href='{{profile}}'>{{name}}</a>'s post",
        profile=url_for('contacts.profile',
                        contact_id=author['id'], _external=True),
        name=author['name']
    )


def render(part, fmt, url=None):
    """
    Attempt to render the PostPart <part> into MIME format <fmt>, which is
    usually 'text/plain' or 'text/html'. There are fall-backs for these two
    formats - otherwise you may have to handle a null return.
    """
    if not url:
        url = url_for('content.raw', part_id=part.mime_part.id)

    ret = None
    renderer = renderer_exists(part.mime_part.type)
    if renderer:
        ret = renderer(part, fmt, url)

    if ret is not None:  # might be empty string!
        return ret

    defaults = {
        'text/html': {
            True: lambda p: render_template_string(
                '{{t}}', t=p.mime_part.text_preview),
            False: lambda p: render_template_string(
                '<a href="{{u}}">(link)</a>', u=url),
        },
        'text/plain': {
            True: lambda p: p.mime_part.text_preview,
            False: lambda p: render_template_string('Link: {{u}}', u=url),
        }
    }

    if fmt in defaults:
        display_inline = bool(part.inline and part.mime_part.text_preview)
        return defaults[fmt][display_inline](part)

    return None
