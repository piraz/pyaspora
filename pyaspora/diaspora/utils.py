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

    if post.diasp and post.diasp.type:
        # Sent before, must keep same type
        private = (post.diasp.type == 'private')
        public = (post.diasp.type == 'public')
    elif post.parent and post.root().diasp and post.root().diasp.type:
        # Reply must be of same type
        root_diasp = post.root().diasp
        private = (root_diasp.type == 'private')
        public = (root_diasp.type == 'public' and self_share.public)
    else:
        # Decide on visibility
        public = self_share.public
        if public:
            private = False
        diasp = DiasporaPost.get_for_post(post, commit=False)
        if public:
            diasp.type = 'public'
        elif private:
            diasp.type = 'private'
        else:
            diasp.type = 'limited'
        db.session.add(diasp)
        db.session.commit()

    if public:
        targets = post.author.friends()
    else:
        shares = set([s.contact_id or s.contact.id for s in post.shares])
        targets = [c for c in targets if c.id in shares]

    json = json_post(post, children=False)
    text = "\n\n".join([p['body']['text'] for p in json['parts']])
    if post.tags:
        text += '\n( ' + ' '.join(
            '#{0}'.format(t.name) for t in post.tags
        ) + ' )'

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

    sender = senders['private' if private else 'public']
    sender = sender['child' if post.parent else 'parent']
    if public:
        # De-dupe by server
        targets = {c.diasp.server: c for c in targets}
        for target in targets.values():
            sender.send_public(post.author.user, target, post=post, text=text)
    else:
        for target in targets:
            sender.send(post.author.user, target, post=post, text=text)


def import_url_as_mimepart(url):
    resp = urlopen(url)
    mp = MimePart()
    mp.type = resp.info().get('Content-Type')
    mp.body = resp.read()
    return mp
