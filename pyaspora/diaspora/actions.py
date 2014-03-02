import json
from base64 import urlsafe_b64encode, urlsafe_b64decode
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5 as PKCSSign
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

    @classmethod
    def struct_to_xml(cls, node, struct):
        for k, v in struct.items():
            etree.SubElement(node, k).text = v

    @classmethod
    def as_dict(cls, xml):
        node = xml[0][0]
        return {e.tag: e.text for e in node}


class SignableMixin:
    @classmethod
    def generate_signature(cls, u_from, node):
        sig_contents = ';'.join([
            e.text for e in node
            if e.text is not None
            and not e.tag.endswith('_signature')
        ])
        print("sig_contents", sig_contents)
        sig_hash = SHA256.new(sig_contents.encode("utf-8"))
        cipher = PKCSSign.new(u_from._unlocked_key)
        return urlsafe_b64encode(cipher.sign(sig_hash))

    @classmethod
    def valid_signature(cls, contact, signature, node):
        signature = urlsafe_b64decode(signature)
        sig_contents = ';'.join([
            e.text for e in node
            if e.text is not None
            and not e.tag.endswith('_signature')
        ])
        print("sig_contents", sig_contents)
        sig_hash = SHA256.new(sig_contents.encode("utf-8"))
        cipher = PKCSSign.new(RSA.importKey(contact.public_key))
        return cipher.verify(sig_hash, signature)


@diaspora_message_handler('/XML/post/request')
class Subscribe(MessageHandlerBase):
    @classmethod
    def receive(cls, xml, c_from, u_to):
        """
        Contact c_from has subcribed to u_to
        """
        data = cls.as_dict(xml)
        assert(data['sender_handle'] == c_from.diasp.username)
        c_from.subscribe(u_to.contact)

    @classmethod
    def generate(cls, u_from, c_to):
        req = etree.Element("request")
        cls.struct_to_xml(req, {
            'sender_handle': u_from.contact.diasp.username,
            'recipient_handle': c_to.diasp.username
        })
        return req


@diaspora_message_handler('/XML/post/profile')
class Profile(MessageHandlerBase):
    @classmethod
    def receive(cls, xml, c_from, u_to):
        data = cls.as_dict(xml)
        assert(data['diaspora_handle'] == c_from.diasp.username)
        c_from.realname = " ".join(
            data.get(k, '') for k in ('first_name', 'last_name')
        )
        c_from.bio = MimePart(
            text_preview=data.get('bio', '(bio)'),
            body=json.dumps(data).encode('utf-8'),
            type='application/x-pyaspora-diaspora-profile'
        )
        if 'image_url' in data:
            c_from.avatar = MimePart(
                text_preview='Image:{0}'.format(data['image_url']),
                body=data['image_url'].encode('ascii'),
                type='application/x-pyaspora-link-image'
            )
        else:
            c_from.avatar = None

        tags = data.get('tag_string', None) or ''
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
        cls.struct_to_xml(req, {
            'diaspora_handle': u_from.contact.diasp.username,
            'first_name': name_parts[0],
            'last_name': name_parts[1],
            'image_url': url_for(
                'contacts.avatar', contact_id=u_from.contact.id, _external=True
            ),
            'birthday': None,
            'gender': None,
            'location': None,
            'searchable': 'true',
            'nsfw': 'false',
            'tag_string': ' '.join(
                '#' + t.name for t in u_from.contact.interests
            )
        })
        return req


@diaspora_message_handler('/XML/post/retraction/type[text()="Person"]')
class Unsubscribe(SignableMixin, MessageHandlerBase):
    @classmethod
    def receive(cls, xml, c_from, u_to):
        data = cls.as_dict(xml)
        assert(data['diaspora_handle'] == c_from.diasp.username)
        assert(data['post_guid'] == c_from.diasp.guid)
        c_from.unsubscribe(u_to.contact)

    @classmethod
    def generate(cls, u_from, c_to):
        req = etree.Element("retraction")
        cls.struct_to_xml(req, {
            'post_guid': u_from.contact.diasp.guid,
            'type': 'Person',
            'diaspora_handle': u_from.contact.diasp.username
        })
        return req


@diaspora_message_handler('/XML/post/status_message')
class PostMessage(MessageHandlerBase):
    @classmethod
    def receive(cls, xml, c_from, u_to):
        data = cls.as_dict(xml)
        assert(data['diaspora_handle'] == c_from.diasp.username)
        created = datetime.strptime(data['created_at'], '%Y-%m-%d %H:%M:%S %Z')
        p = Post(author=c_from, created_at=created)
        p.add_part(MimePart(
            type='text/x-markdown',
            body=data['raw_message'].encode('utf-8'),
        ), order=0, inline=True)
        p.share_with([c_from, u_to.contact])
        p.thread_modified()

        p.diasp = DiasporaPost(guid=data['guid'])
        db.session.commit()

    @classmethod
    def generate(cls, u_from, c_to, post, text, public):
        diasp = DiasporaPost.get_for_post(post)
        req = etree.Element("status_message")
        cls.struct_to_xml(req, {
            'raw_message': text,
            'guid': diasp.guid,
            'diaspora_handle': u_from.contact.diasp.username,
            'public': 'true' if public else 'false',
            'created_at': post.created_at.isoformat()
        })
        return req


@diaspora_message_handler('/XML/post/conversation')
class PrivateMessage(MessageHandlerBase):
    @classmethod
    def receive(cls, xml, c_from, u_to):
        data = cls.as_dict(xml)
        assert(data['diaspora_handle'] == c_from.diasp.username)
        created = datetime.strptime(data['created_at'], '%Y-%m-%d %H:%M:%S %Z')

        p = Post(author=c_from, created_at=created)
        part_tags = [t for t in ('subject', 'text') if t in data]
        for order, tag in part_tags:
            p.add_part(MimePart(
                type='text/plain',
                body=data[tag].encode('utf-8'),
            ), order=order, inline=True)
        p.share_with([c_from, u_to.contact])
        p.thread_modified()
        db.session.commit()

        p.diasp = DiasporaPost(guid=data['guid'])
        db.session.commit()

    @classmethod
    def generate(cls, u_from, c_to, post, text):
        req = etree.Element("conversation")
        diasp = DiasporaPost.get_for_post(post)
        cls.struct_to_xml(req, {
            'guid': diasp.guid,
            'subject': '(no subject)',
            'created_at': post.created_at.isoformat(),
            'diaspora_handle': u_from.contact.diasp.username,
            'participant_handles': ';'.join(
                c.diasp.username for c in post.shares if c.diasp
            )
        })
        msg = etree.SubElement(req, "message")
        cls.struct_to_xml(msg, {
            'guid': diasp.guid + '-1',
            'parent_guid': None,
            'text': text,
            'created_at': post.created_at.isoformat(),
            'conversation_guid': diasp.guid
        })
        #etree.SubElement(msg, "parent_author_signature")
        etree.SubElement(msg, "author_signature").text = \
            cls.generate_signature(u_from, req)

        return req


@diaspora_message_handler('/XML/post/participation/target_type[text()="Post"]')
class PostParticipation(MessageHandlerBase):
    @classmethod
    def receive(cls, xml, c_from, u_to):
        # Not sure what these do, but they don't seem to be necessary, so do
        # nothing - like Shares?
        pass


@diaspora_message_handler('/XML/post/message')
@diaspora_message_handler('/XML/post/comment')
class SubPost(SignableMixin, MessageHandlerBase):
    @classmethod
    def receive(cls, xml, c_from, u_to):
        data = cls.as_dict(xml)
        assert(data['diaspora_handle'] == c_from.diasp.username)
        body = data['text']
        parent = DiasporaPost.get_by_guid(data['parent_guid']).post
        assert(parent)
        assert(parent.shared_with(c_from))
        assert(parent.shared_with(u_to))
        assert(cls.valid_signature(c_from, data['author_signature'], node))
        if 'parent_author_signature' in data:
            assert(
                cls.valid_signature(
                    c_from, data['parent_author_signature'], node
                )
            )

        p = Post(author=c_from)
        p.parent = parent
        p.add_part(MimePart(
            type='text/plain',
            body=body.encode('utf-8'),
        ), order=0, inline=True)
        p.share_with([c_from, u_to.contact])
        p.thread_modified()

        p.diasp = DiasporaPost(guid=data['guid'])
        db.session.commit()

    @classmethod
    def generate(cls, u_from, c_to, post, text, msg_type='comment'):
        req = etree.Element(msg_type)
        diasp = DiasporaPost.get_for_post(post)
        p_diasp = DiasporaPost.get_for_post(post.parent)

        cls.struct_to_xml(req, {
            'guid': diasp.guid,
            'parent_guid': p_diasp.guid,
            'text': text,
            'diaspora_handle': u_from.contact.diasp.username
        })
        etree.SubElement(req, "author_signature").text = \
            cls.generate_signature(u_from, req)
        if post.parent.author_id == u_from.id:
            etree.SubElement(req, "parent_author_signature").text = \
                cls.generate_signature(u_from, req)
        return req


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
        data = cls.as_dict(xml)
        assert(data['diaspora_handle'] == c_from.diasp.username)
        parent = DiasporaPost.get_by_guid(data['guid']).post
        assert(parent)
        assert(parent.shared_with(c_from))
        assert(parent.shared_with(u_to))
        photo_url = urljoin(
            data['remote_photo_path'], data['remote_photo_name']
        )
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
