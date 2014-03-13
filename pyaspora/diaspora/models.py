from __future__ import absolute_import

from base64 import b64decode
from flask import current_app, request, url_for
from lxml import html
from sqlalchemy import Column, DateTime, ForeignKey, Integer, LargeBinary, \
    String
from sqlalchemy.orm import backref, relationship
from sqlalchemy.sql import and_
from sqlalchemy.sql.expression import func
from traceback import format_exc
from uuid import uuid4
try:
    from urllib.error import URLError
    from urllib.parse import urljoin, urlsplit, urlunsplit
    from urllib.request import urlopen
except:
    from urllib import urlopen
    from urllib2 import URLError
    from urlparse import urljoin, urlsplit, urlunsplit

from pyaspora import db
from pyaspora.contact.models import Contact
from pyaspora.diaspora import import_url_as_mimepart
from pyaspora.diaspora.protocol import DiasporaMessageParser, WebfingerRequest
from pyaspora.post.views import json_post


class DiasporaContact(db.Model):
    __tablename__ = 'diaspora_contacts'
    contact_id = Column(Integer, ForeignKey('contacts.id'), primary_key=True)
    guid = Column(String, nullable=False, unique=True)
    username = Column(String, nullable=False)
    server = Column(String, nullable=False)

    contact = relationship('Contact', single_parent=True,
                           backref=backref('diasp', uselist=False))

    @classmethod
    def get_for_contact(cls, contact, commit=True):
        if contact.diasp:
            return contact.diasp
        assert(contact.user)
        server = urlunsplit(list(urlsplit(request.url)[0:2]) + ['/', '', ''])
        diasp = cls(
            server=server,
            guid=str(uuid4()),
            username="{0}@{1}".format(contact.user.id, server),
            contact=contact
        )
        db.session.add(diasp)
        if commit:
            db.session.commit()
        return diasp

    @classmethod
    def get_by_guid(cls, guid):
        print("look up", guid)
        return db.session.query(cls).filter(cls.guid == guid).first()

    @classmethod
    def get_by_username(cls, addr, import_contact=True, commit=True):
        dcontact = db.session.query(DiasporaContact).filter(
            cls.username == addr).first()
        if dcontact:
            return dcontact

        if import_contact:
            contact = cls.import_contact(addr)
            if commit:
                db.session.commit()
        return contact

    @classmethod
    def import_contact(cls, addr):
        """
        Fetch information about a Diaspora user and import it into the Contact
        provided.
        """
        try:
            wf = WebfingerRequest(addr).fetch()
        except URLError:
            return None
        if not wf:
            return None

        NS = {'XRD': 'http://docs.oasis-open.org/ns/xri/xrd-1.0'}

        c = Contact()

        pk = wf.xpath('//XRD:Link[@rel="diaspora-public-key"]/@href',
                      namespaces=NS)[0]
        c.public_key = b64decode(pk).decode("ascii")

        hcard_url = wf.xpath(
            '//XRD:Link[@rel="http://microformats.org/profile/hcard"]/@href',
            namespaces=NS
        )[0]
        hcard = html.parse(urlopen(hcard_url))
        c.realname = hcard.xpath('//*[@class="fn"]')[0].text

        pod_loc = hcard.xpath('//*[@id="pod_location"]')[0].text
        photo_url = hcard.xpath('//*[@class="entity_photo"]//img/@src')[0]
        if photo_url:
            mp = import_url_as_mimepart(urljoin(pod_loc, photo_url))
            mp.text_preview = '(picture for {})'.format(c.realname)
            c.avatar = mp

        username = wf.xpath(
            '//XRD:Subject/text()',
            namespaces=NS
        )[0].split(':')[1]
        guid = wf.xpath(
            ".//XRD:Link[@rel='http://joindiaspora.com/guid']",
            namespaces=NS
        )[0].get("href")
        server = wf.xpath(
            ".//XRD:Link[@rel='http://joindiaspora.com/seed_location']",
            namespaces=NS
        )[0].get("href")
        d = cls(
            contact=c,
            guid=guid,
            username=username,
            server=server
        )
        db.session.add(d)
        db.session.add(c)

        return d

    def photo_url(self):
        """
        Diaspora requires all contacts have pictures, even if they haven't
        chosen one. This call returns a default if a picture hasn't been
        uploaded.
        """
        if self.contact.avatar:
            return url_for(
                'contacts.avatar',
                contact_id=self.contact_id,
                _external=True
            )
        else:
            return url_for(
                'static',
                filename='nophoto.png',
                _external=True
            )


class MessageQueue(db.Model):
    """
    Messages that have been received but that cannot be actioned until the
    User's public key has been unlocked (at which point they will be deleted).

    Fields:
        id - an integer identifier uniquely identifying the message in the
             queue
        local_id - the User receiving/sending the message
        remote_id - the Contact the message is to/from
        format - the protocol format of the payload
        body - the message payload, in a protocol-specific format
    """
    OUTGOING = 'application/x-pyaspora-outbound'
    INCOMING = 'application/x-diaspora-slap'

    __tablename__ = 'message_queue'
    id = Column(Integer, primary_key=True)
    local_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    remote_id = Column(Integer, ForeignKey('contacts.id'), nullable=True)
    format = Column(String, nullable=False)
    body = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime(timezone=True),
                        nullable=False, default=func.now())
    error = Column(LargeBinary, nullable=True)

    local_user = relationship('User', backref='message_queue')

    class Queries:
        @classmethod
        def pending_items_for_user(cls, user):
            return and_(
                MessageQueue.format == MessageQueue.INCOMING,
                MessageQueue.local_user == user
            )

    @classmethod
    def has_pending_items(cls, user):
        first = db.session.query(cls).filter(
            cls.Queries.pending_items_for_user(user)
        ).order_by(cls.created_at).first()
        return bool(first and not first.error)

    @classmethod
    def process_incoming_queue(cls, user, max_items=None):
        from pyaspora.diaspora.actions import process_incoming_message

        queue_items = db.session.query(MessageQueue).filter(
            cls.Queries.pending_items_for_user(user)
        ).order_by(cls.created_at)
        dmp = DiasporaMessageParser(DiasporaContact.get_by_username)
        processed = 0
        for qi in queue_items:
            if qi.error:
                break

            ret, c_from = dmp.decode(
                qi.body.decode('ascii'),
                user._unlocked_key
            )
            try:
                process_incoming_message(ret, c_from, user)
                processed += 1
                if max_items and processed > max_items:
                    break
            except Exception:
                err = format_exc()
                qi.error = err.encode('utf-8')
                current_app.logger.error(err)
                db.session.add(qi)
                break
            else:
                db.session.delete(qi)
        db.session.commit()


class DiasporaPost(db.Model):
    __tablename__ = 'diaspora_posts'
    post_id = Column(Integer, ForeignKey('posts.id'), primary_key=True)
    guid = Column(String, nullable=False)
    type = Column(String, nullable=True)

    post = relationship('Post', single_parent=True,
                        backref=backref('diasp', uselist=False))

    @classmethod
    def get_for_post(cls, post, commit=True):
        if post.diasp:
            return post.diasp
        assert(post.author.user)
        diasp = cls(
            guid=str(uuid4()),
            post=post
        )
        db.session.add(diasp)
        if commit:
            db.session.commit()
        return diasp

    @classmethod
    def get_by_guid(cls, guid):
        return db.session.query(cls).filter(cls.guid == guid).first()

    def as_text(self):
        json = json_post(self.post, children=False)
        text = "\n\n".join([p['body']['text'] for p in json['parts']])
        if self.post.tags:
            text += '\n( ' + ' '.join(
                '#{0}'.format(t.name) for t in self.post.tags
            ) + ' )'
        return text

    def send_to(self, targets, private=False):
        from pyaspora.diaspora.actions import PostMessage, PrivateMessage, \
            SubPost, SubPM

        post = self.post

        assert(post.author.user)

        self_share = post.shared_with(post.author)
        assert(self_share)

        if self.type:
            # Sent before, must keep same type
            private = (self.type == 'private')
            public = (self.type == 'public')
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
                self.type = 'public'
            elif private:
                self.type = 'private'
            else:
                self.type = 'limited'

        text = self.as_text()

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
            targets = dict((c.diasp.server, c) for c in targets)
            for target in targets.values():
                sender.send_public(
                    post.author.user,
                    target,
                    post=post,
                    text=text
                )
        else:
            for target in targets:
                sender.send(post.author.user, target, post=post, text=text)

    def can_change_privacy(self):
        return False  # Generally, no

    def can_reply_with(self, target):
        if target.name == 'self':
            return True
        if self.type and self.type == 'p':
            return target.name == 'public'
        else:
            return target.name == 'existing'
