from __future__ import absolute_import

from sqlalchemy.sql import and_
try:
    from urllib.request import urlopen
except:
    from urllib import urlopen

from pyaspora.content.models import MimePart
from pyaspora.database import db
from pyaspora.diaspora.models import DiasporaContact, DiasporaPost, \
    MessageQueue
from pyaspora.diaspora.protocol import DiasporaMessageParser
from pyaspora.post.views import json_post
from pyaspora.roster.models import Subscription


def import_url_as_mimepart(url):
    resp = urlopen(url)
    mp = MimePart()
    mp.type = resp.info().get('Content-Type')
    mp.body = resp.read()
    return mp
