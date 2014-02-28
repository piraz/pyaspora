from base64 import b64decode
from flask import request
from lxml import html
from sqlalchemy import Column, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import backref, relationship
from uuid import uuid4
try:
    from urllib.error import URLError
    from urllib.parse import urljoin, urlsplit
    from urllib.request import urlopen
except:
    from urllib import urlopen
    from urllib2 import URLError
    from urlparse import urljoin, urlsplit

from pyaspora import db
from pyaspora.contact.models import Contact
from pyaspora.content.models import MimePart
from pyaspora.diaspora.protocol import WebfingerRequest


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
        server = urlsplit(request.url)[1]
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
            return dcontact.contact

        if import_contact:
            contact = import_contact(addr)
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

        photo_url = hcard.xpath('//*[@class="entity_photo"]//img/@src')
        if photo_url:
            resp = urlopen(urljoin(hcard_url, photo_url[0]))
            mp = MimePart()
            mp.type = resp.info().get('Content-Type')
            mp.body = resp.read()
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

        return c


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

    local_user = relationship('User', backref='message_queue')


class DiasporaPost(db.Model):
    __tablename__ = 'diaspora_posts'
    post_id = Column(Integer, ForeignKey('posts.id'), primary_key=True)
    guid = Column(String, nullable=False)

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
