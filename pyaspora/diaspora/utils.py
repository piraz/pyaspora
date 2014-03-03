from sqlalchemy.sql import and_
try:
    from urllib.request import urlopen
except:
    from urllib import urlopen

from pyaspora.content.models import MimePart
from pyaspora.database import db
from pyaspora.diaspora.models import DiasporaContact, MessageQueue
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
    )
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


def send_post(post, private):
    from pyaspora.diaspora.actions import PostMessage, PrivateMessage, \
        SubPost, SubPM

    assert(post.author.user)

    self_share = [s for s in post.shares if post.author == s.contact][0]
    assert(self_share)

    # All people interested in the author
    targets = db.session.query(Subscription).filter(
        Subscription.to_contact == post.author
    )
    targets = [s.from_contact for s in targets if s.from_contact.diasp]
    if not self_share.public:
        shares = set([s.contact_id or s.contact.id for s in post.shares])
        targets = [c for c in targets if c.id in shares]

    json = json_post(post, children=False)
    text = "\n\n".join([p['body']['text'] for p in json['parts']])

    senders = {
        'private': {
            'parent': PrivateMessage,
            'child': SubPM,
        },
        'public': {
            'parent': PostMessage,
            'child': SubPost,
        }
    }

    for target in targets:
        sender = senders['private' if private else 'public']
        sender = sender['child' if post.parent else 'parent']
        sender.send(post.author.user, target, post=post, text=text)


def import_url_as_mimepart(url):
    resp = urlopen(url)
    mp = MimePart()
    mp.type = resp.info().get('Content-Type')
    mp.body = resp.read()
    return mp
