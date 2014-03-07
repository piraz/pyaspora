from flask import request

try:
    from urllib.parse import urlsplit, urlunsplit
except:
    from urlparse import urlsplit, urlunsplit


def get_server_name():
    return urlsplit(request.url).netloc
