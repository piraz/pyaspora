from __future__ import absolute_import

from flask import render_template_string, url_for
from json import loads
from markdown import Markdown
try:
    from markdown.extensions import Extension
except:
    from markdown import Extension
from markdown.preprocessors import Preprocessor
from re import compile as re_compile

from pyaspora.utils.rendering import ACCEPTABLE_BROWSER_IMAGE_FORMATS

renderers = {}


class SkipTagsExtension(Extension):
    class SkipTagPattern(Preprocessor):
        """
        Look for lines of tags and stop them becoming headings. It does this by
        putting a space before the line.
        """
        def __init__(self):
            self.pattern = re_compile(r'^(#([A-Za-z0-9_]+(\s+#)?)+)$')

        def run(self, lines):
            return [
                self.pattern.sub(r' \1', l) for l in lines
            ]

    def extendMarkdown(self, md, md_globals):
        md.preprocessors.add('skiptags', self.SkipTagPattern(), '_end')


def _markdown_to_html(md_text):
    common_opts = dict(
        output_format='xhtml',
        safe_mode='replace',
        extensions=['headerid(forceid=False, level=3)', SkipTagsExtension()]
    )
    try:
        md = Markdown(
            html_replacement_text='(could not show this)',
            lazy_ol=False,
            **common_opts
        )
    except TypeError:
        md = Markdown(
            **common_opts
        )
    return md.convert(md_text)


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
                text=part.mime_part.body.decode('utf-8')
            )
        if fmt == 'text/plain':
            return part.mime_part.body.decode('utf-8')
    return None


@renderer(['text/html'])
def text_html(part, fmt, url):
    """
    Renderer for text/html.
    """
    if part.inline and fmt == 'text/html':
        return part.mime_part.body.decode('utf-8')
    return None


@renderer(['text/x-markdown'])
def text_markdown(part, fmt, url):
    """
    Renderer for text/x-markdown (MarkDown).
    """
    if part.inline:
        md = part.mime_part.body.decode('utf-8')
        if fmt == 'text/html':
            return _markdown_to_html(md)
        if fmt == 'text/plain':
            return md
    return None


@renderer(ACCEPTABLE_BROWSER_IMAGE_FORMATS)
def common_images(part, fmt, url):
    """
    Renderer for image/* that a browser can display in an <img> tag.
    """
    if fmt == 'text/html' and part.inline:
        return render_template_string(
            '<img src="{{url}}" alt="{{alt}}" />',
            url=url_for(
                'content.raw',
                part_id=part.mime_part.id,
                _external=True
            ),
            alt=part.mime_part.text_preview
        )


@renderer(['application/x-pyaspora-subscribe'])
def pyaspora_subscribe(part, fmt, url):
    """
    Standard message for when a contact subscribes to you.
    """
    if fmt != 'text/html' or not part.inline:
        return None

    payload = loads(part.mime_part.body.decode('utf-8'))
    return render_template_string(
        'subscribed to <a href="{{profile}}">{{name}}</a>',
        profile=url_for(
            'contacts.profile',
            contact_id=payload['to'],
            _external=True
        ),
        name=payload.get('to_name', '(unknown)')
    )


@renderer(['application/x-pyaspora-share'])
def pyaspora_share(part, fmt, url):
    """
    Standard message for when a post is shared.
    """
    if fmt != 'text/html' or not part.inline:
        return None

    payload = loads(part.mime_part.body.decode('utf-8'))
    author = payload['author']
    return render_template_string(
        "shared <a href='{{profile}}'>{{name}}</a>'s post",
        profile=url_for(
            'contacts.profile',
            contact_id=author['id'],
            _external=True
        ),
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


@renderer(['application/x-pyaspora-diaspora-profile'])
def diaspora_profile(part, fmt, url):
    """
    Renders a Diaspora profile received from a remote server. Diaspora has
    rather more feature-rich profiles than Pyaspora.
    """
    payload = loads(part.mime_part.body.decode('utf-8'))
    payload['parsed_bio'] = _markdown_to_html(payload.get('bio', None) or '')
    if fmt != 'text/html' or not part.inline:
        return None

    templ = """
    <p>{{parsed_bio or '(no info)' |safe}}</p>
    <table>
        {%- if gender %}
        <tr>
            <th>Gender</th>
            <td>{{gender}}</td>
        </tr>
        {% endif -%}
        {%- if birthday %}
        <tr>
            <th>Birthday</th>
            <td>{{birthday}}</td>
        </tr>
        {% endif -%}
        {%- if location %}
        <tr>
            <th>Location</th>
            <td>{{location}}</td>
        </tr>
        {% endif -%}
    </table>
    """
    return render_template_string(templ, **payload)
