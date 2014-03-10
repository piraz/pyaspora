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


def process_incoming_queue(user):
    from pyaspora.diaspora.actions import process_incoming_message

    # FIXME order by time received
    queue_items = db.session.query(MessageQueue).filter(
        and_(
            MessageQueue.format == MessageQueue.INCOMING,
            MessageQueue.local_user == user
        )
    ).order_by(MessageQueue.created_at)
    dmp = DiasporaMessageParser(DiasporaContact.get_by_username)
    for qi in queue_items:
        ret, c_from = dmp.decode(qi.body.decode('ascii'), user._unlocked_key)
        try:
            process_incoming_message(ret, c_from, user)
        except Exception:
            import traceback
            traceback.print_exc()
        else:
            db.session.delete(qi)
    db.session.commit()




def import_url_as_mimepart(url):
    resp = urlopen(url)
    mp = MimePart()
    mp.type = resp.info().get('Content-Type')
    mp.body = resp.read()
    return mp
