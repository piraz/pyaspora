from urllib.parse import parse_qsl, urlsplit, urlunsplit

QUERY = 3


def chunk_url_params(url):
    """
    Utility to allow Jinja to extract the query string parameters out of a
    URL, so that they can be converted into hidden fields.
    """
    url_parts = list(urlsplit(url))
    qs_parts = parse_qsl(url_parts[QUERY])
    url_parts[QUERY] = ''
    return (urlunsplit(url_parts), qs_parts)
