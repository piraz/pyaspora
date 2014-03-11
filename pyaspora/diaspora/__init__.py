from __future__ import absolute_import

try:
    from urllib.request import urlopen
except:
    from urllib import urlopen

from pyaspora.content.models import MimePart


def import_url_as_mimepart(url):
    resp = urlopen(url)
    mp = MimePart()
    mp.type = resp.info().get('Content-Type')
    mp.body = resp.read()
    return mp
