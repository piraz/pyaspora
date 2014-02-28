import json
from Crypto.PublicKey import RSA
from flask import url_for
from datetime import datetime
from lxml import etree
try:
    from urllib.error import URLError
    from urllib.parse import urljoin
    from urllib.request import urlopen
except:
    from urllib import urlopen
    from urllib2 import URLError
    from urlparse import urljoin

from pyaspora import db
from pyaspora.content.models import MimePart
from pyaspora.diaspora.models import DiasporaContact, DiasporaPost
from pyaspora.diaspora.protocol import DiasporaMessageBuilder
from pyaspora.post.models import Post
from pyaspora.tag.models import Tag

HANDLERS = {}


def diaspora_message_handler(xpath):
    def _inner(cls):
        HANDLERS[xpath] = cls
        return cls
    return _inner


def process_incoming_message(payload, c_from, u_to):
    xml = payload.lstrip()
    print(xml)
    doc = etree.fromstring(xml)
    for xpath, handler in HANDLERS.items():
        if doc.xpath(xpath):
            return handler.receive(doc, c_from, u_to)
    raise Exception("No handler registered", payload)


class MessageHandlerBase:
    @classmethod
    def send(cls, u_from, c_to, **kwargs):
        diasp = DiasporaContact.get_for_contact(u_from.contact)
        xml = cls.generate(u_from, c_to, **kwargs)
        m = DiasporaMessageBuilder(xml, diasp.username, u_from._unlocked_key)
        url = "{0}receive/users/{1}".format(
            c_to.diasp.server, c_to.diasp.guid)
        print("posting {0} to {1}".format(etree.tostring(xml), url))
        resp = m.post(url, RSA.importKey(c_to.public_key))
        return resp


@diaspora_message_handler('/XML/post/request')
class Subscribe(MessageHandlerBase):
    @classmethod
    def receive(cls, xml, c_from, u_to):
        """
        Contact c_from has subcribed to u_to
        """
        from_addr = xml.xpath('//sender_handle')[0].text
        assert(from_addr == c_from.diasp.username)
        c_from.subscribe(u_to.contact)

    @classmethod
    def generate(cls, u_from, c_to):
        req = etree.Element("request")
        etree.SubElement(req, "sender_handle").text = \
            u_from.contact.diasp.username
        etree.SubElement(req, "recipient_handle").text = c_to.diasp.username
        return req


@diaspora_message_handler('/XML/post/profile')
class Profile(MessageHandlerBase):
    @classmethod
    def receive(cls, xml, c_from, u_to):
        from_addr = xml.xpath('//diaspora_handle')[0].text
        assert(from_addr == c_from.diasp.username)
        first_name = xml.xpath('//first_name')
        first_name = first_name[0].text if first_name else None
        last_name = xml.xpath('//last_name')
        last_name = last_name[0].text if last_name else None
        image_url = xml.xpath('//image_url')[0].text
        tags = xml.xpath('//tag_string')[0].text or ''
        body = {e.tag: e.text for e in xml.xpath('//profile')[0]}
        c_from.realname = " ".join([first_name or '', last_name or ''])
        bio = xml.xpath('//bio')
        c_from.bio = MimePart(
            text_preview=bio[0].text if bio else '(bio)',
            body=json.dumps(body).encode('utf-8'),
            type='application/x-pyaspora-diaspora-profile'
        )
        if image_url:
            c_from.avatar = MimePart(
                text_preview='Image:{0}'.format(image_url),
                body=image_url.encode('ascii'),
                type='application/x-pyaspora-link-image'
            )
        else:
            c_from.avatar = None

        tags = ' '.join(tags.split('#'))
        c_from.interests = Tag.parse_line(tags)

        db.session.add(c_from)
        db.session.commit()

    @classmethod
    def generate(cls, u_from, c_to):
        req = etree.Element("profile")
        name_parts = u_from.contact.realname.split(maxsplit=2)
        if len(name_parts) == 1:
            name_parts.append('')
        etree.SubElement(req, "diaspora_handle").text = \
            u_from.contact.diasp.username
        etree.SubElement(req, "first_name").text = name_parts[0]
        etree.SubElement(req, "last_name").text = name_parts[1]
        etree.SubElement(req, "image_url").text = \
            url_for('contacts.avatar', contact_id=u_from.contact.id)
        etree.SubElement(req, "birthday")
        etree.SubElement(req, 'gender')
        etree.SubElement(req, 'location')
        etree.SubElement(req, 'searchable').text = 'true'
        etree.SubElement(req, 'nsfw').text = 'false'
        etree.SubElement(req, 'tag_string').text = \
            ' '.join(['#' + t.name for t in u_from.contact.interests])
        return req


@diaspora_message_handler('/XML/post/retraction/type[text()="Person"]')
class Unsubscribe(MessageHandlerBase):
    @classmethod
    def receive(cls, xml, c_from, u_to):
        from_addr = xml.xpath('//diaspora_handle')[0].text
        assert(from_addr == c_from.diasp.username)
        c_from.unsubscribe(u_to.contact)

    @classmethod
    def generate(cls, u_from, c_to):
        req = etree.Element("retraction")
        etree.SubElement(req, "post_guid")
        etree.SubElement(req, "diaspora_handle").text = \
            u_from.contact.diasp.username
        etree.SubElement(req, "type").text = 'Person'
        return req


@diaspora_message_handler('/XML/post/status_message')
class PostMessage(MessageHandlerBase):
    @classmethod
    def receive(cls, xml, c_from, u_to):
        from_addr = xml.xpath('//diaspora_handle')[0].text
        assert(from_addr == c_from.diasp.username)
        body = xml.xpath('//raw_message')[0].text
        created = xml.xpath('//created_at')[0].text
        created = datetime.strptime(created, '%Y-%m-%d %H:%M:%S %Z')
        p = Post(author=c_from, created_at=created)
        p.add_part(MimePart(
            type='text/x-markdown',
            body=body.encode('utf-8'),
        ), order=0, inline=True)
        p.share_with([c_from, u_to.contact])
        p.thread_modified()

        guid = xml.xpath('//guid')[0].text
        p.diasp = DiasporaPost(guid=guid)
        db.session.commit()

    @classmethod
    def generate(cls, u_from, c_to, post, text, public):
        diasp = DiasporaPost.get_for_post(post)
        req = etree.Element("status_message")
        etree.SubElement(req, "raw_message").text = text
        etree.SubElement(req, "guid").text = diasp.guid
        etree.SubElement(req, "diaspora_handle").text = \
            u_from.contact.diasp.username
        etree.SubElement(req, "public").text = 'true' if public else 'false'
        etree.SubElement(req, "created_at").text = post.created_at.isoformat()
        return req


@diaspora_message_handler('/XML/post/conversation')
class PrivateMessage(MessageHandlerBase):
    @classmethod
    def receive(cls, xml, c_from, u_to):
        from_addr = xml.xpath('//diaspora_handle')[0].text
        assert(from_addr == c_from.diasp.username)
        body = xml.xpath('//text')[0].text
        subject = xml.xpath('//subject')[0].text
        created = xml.xpath('//created_at')[0].text
        created = datetime.strptime(created, '%Y-%m-%d %H:%M:%S %Z')
        p = Post(author=c_from, created_at=created)
        if subject:
            p.add_part(MimePart(
                type='text/plain',
                body=subject.encode('utf-8'),
            ), order=0, inline=True)
        if body:
            p.add_part(MimePart(
                type='text/plain',
                body=body.encode('utf-8'),
            ), order=1 if subject else 0, inline=True)
        p.share_with([c_from, u_to.contact])
        p.thread_modified()
        db.session.commit()

        guid = xml.xpath('//guid')[0].text
        p.diasp = DiasporaPost(guid=guid)
        db.session.commit()

    @classmethod
    def generate(cls, u_from, c_to, post, text):
        req = etree.Element("conversation")
        diasp = DiasporaPost.get_for_post(post)
        etree.SubElement(req, "guid").text = diasp.guid
        etree.SubElement(req, "subject").text = '(no subject)'
        etree.SubElement(req, "created_at").text = post.created_at.isoformat()
        msg = etree.SubElement(req, "message")
        etree.SubElement(msg, "guid").text = diasp.guid + '-1'
        etree.SubElement(msg, "parent_guid")
        etree.SubElement(msg, "parent_author_signature")
        etree.SubElement(msg, "author_signature")
        etree.SubElement(msg, "text").text = text
        etree.SubElement(msg, "created_at").text = post.created_at.isoformat()
        etree.SubElement(msg, "conversation_guid").text = \
            diasp.guid
        etree.SubElement(req, "diaspora_handle").text = \
            u_from.contact.diasp.username
        etree.SubElement(req, "participant_handles").text = \
            ';'.join([c_to.diasp.username, u_from.contact.diasp.username])
        return req


@diaspora_message_handler('/XML/post/participation/target_type[text()="Post"]')
class PostParticipation(MessageHandlerBase):
    @classmethod
    def receive(cls, xml, c_from, u_to):
        # Not sure what these do, but they don't seem to be necessary, so do
        # nothing
        pass


@diaspora_message_handler('/XML/post/message')
@diaspora_message_handler('/XML/post/comment')
class SubPost(MessageHandlerBase):
    @classmethod
    def receive(cls, xml, c_from, u_to):
        from_addr = xml.xpath('//diaspora_handle')[0].text
        assert(from_addr == c_from.diasp.username)
        body = xml.xpath('//text')[0].text
        parent_guid = xml.xpath('//parent_guid')[0].text
        parent = DiasporaPost.get_by_guid(parent_guid).post
        assert(parent)
        assert(parent.shared_with(c_from))
        assert(parent.shared_with(u_to))
        p = Post(author=c_from)
        p.parent = parent
        p.add_part(MimePart(
            type='text/plain',
            body=body.encode('utf-8'),
        ), order=0, inline=True)
        p.share_with([c_from, u_to.contact])
        p.thread_modified()

        guid = xml.xpath('//guid')[0].text
        p.diasp = DiasporaPost(guid=guid)
        db.session.commit()


@diaspora_message_handler('/XML/post/like')
class Like(MessageHandlerBase):
    @classmethod
    def receive(cls, xml, c_from, u_to):
        # Pyaspora does not support likes
        pass


@diaspora_message_handler('/XML/post/relayable_retraction')
@diaspora_message_handler('/XML/post/signed_retraction')
class Retraction(MessageHandlerBase):
    @classmethod
    def receive(cls, xml, c_from, u_to):
        # Pyaspora does not support deleting posts/PMs
        pass


@diaspora_message_handler('/XML/post/photo')
class Photo(MessageHandlerBase):
    @classmethod
    def receive(cls, xml, c_from, u_to):
        from_addr = xml.xpath('//diaspora_handle')[0].text
        assert(from_addr == c_from.diasp.username)
        parent_guid = xml.xpath('//guid')[0].text
        parent = DiasporaPost.get_by_guid(parent_guid).post
        assert(parent)
        assert(parent.shared_with(c_from))
        assert(parent.shared_with(u_to))
        directory = xml.xpath('//remote_photo_path')[0].text
        file = xml.xpath('//remote_photo_name')[0].text
        photo_url = urljoin(directory, file)
        resp = urlopen(photo_url)
        mime = resp.info().get('Content-Type')
        parent.add_part(MimePart(
            type=resp.info().get('Content-Type'),
            body=resp.read(),
            text_preview='(picture)'
        ), order=0, inline=bool(mime.startswith('image/')))
        parent.thread_modified()
        db.session.add(parent)
        db.session.commit()
