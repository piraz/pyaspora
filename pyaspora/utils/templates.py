import re
from jinja2 import evalcontextfilter, Markup, escape

try:
    from urllib.parse import parse_qsl, urlsplit, urlunsplit  # py3
except ImportError:
    from urlparse import parse_qsl, urlsplit, urlunsplit  # py2

QUERY = 3
_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')


@evalcontextfilter
def nl2br(eval_ctx, value):
    result = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', '<br>\n') \
        for p in _paragraph_re.split(escape(value)))
    if eval_ctx.autoescape:
        result = Markup(result)
    return result

def chunk_url_params(url):
    """
    Utility to allow Jinja to extract the query string parameters out of a
    URL, so that they can be converted into hidden fields.
    """
    url_parts = list(urlsplit(url))
    qs_parts = parse_qsl(url_parts[QUERY])
    url_parts[QUERY] = ''
    return (urlunsplit(url_parts), qs_parts)
