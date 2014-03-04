from re import compile as re_compile
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil.tz import tzutc
from jinja2 import evalcontextfilter, Markup, escape
try:
    from urllib.parse import parse_qsl, urlsplit, urlunsplit  # py3
except ImportError:
    from urlparse import parse_qsl, urlsplit, urlunsplit  # py2

from pyaspora.utils.rendering import ensure_timezone

QUERY = 3
_paragraph_re = re_compile(r'(?:\r\n|\r|\n){2,}')


@evalcontextfilter
def nl2br(eval_ctx, value):
    result = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', '<br>\n')
                          for p in _paragraph_re.split(escape(value)))
    if eval_ctx.autoescape:
        result = Markup(result)
    return result


def since(dt, base=None, chunks=1):
    if not base:
        base = datetime.now()

    if isinstance(dt, str):
        dt = datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S')

    if dt == base:
        return "now"

    if dt < base:
        delta = relativedelta(base, dt)
        prefix = ''
        suffix = ' ago'
    else:
        delta = relativedelta(dt, base)
        prefix = 'in '
        suffix = ''

    sections = (
        ('years', None),
        ('months', None),
        ('weeks', lambda r: int(r.days / 7)),
        ('days', lambda r: r.days % 7),
        ('hours', None),
        ('minutes', None),
        ('seconds', None)
    )

    result = []
    for section, handler in sections:
        if handler:
            val = handler(delta)
        else:
            val = getattr(delta, section, None)
        if val:
            result.append('{0} {1}'.format(val, section if val != 1 else section[:-1]))
        if chunks and len(result) >= chunks:
            break
    return prefix + ', '.join(result) + suffix


def chunk_url_params(url):
    """
    Utility to allow Jinja to extract the query string parameters out of a
    URL, so that they can be converted into hidden fields.
    """
    url_parts = list(urlsplit(url))
    qs_parts = parse_qsl(url_parts[QUERY])
    url_parts[QUERY] = ''
    return (urlunsplit(url_parts), qs_parts)
