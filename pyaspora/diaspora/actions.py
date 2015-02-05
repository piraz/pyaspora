from __future__ import absolute_import

from base64 import b64encode, b64decode
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5 as PKCSSign
from datetime import datetime
from dateutil.tz import tzutc
from flask import current_app, url_for
from json import dumps
from lxml import etree
from re import compile as re_compile
try:
    from urllib.parse import urljoin
    from urllib.request import urlopen
except:
    from urllib2 import urlopen
    from urlparse import urljoin

from pyaspora import db
from pyaspora.content.models import MimePart
from pyaspora.diaspora import import_url_as_mimepart
from pyaspora.diaspora.models import DiasporaContact, DiasporaPart, \
    DiasporaPost, TryLater
from pyaspora.diaspora.protocol import DiasporaMessageBuilder
from pyaspora.post.models import Post
from pyaspora.roster.models import Subscription
from pyaspora.tag.models import Tag
from pyaspora.utils.rendering import ensure_timezone

HANDLERS = {}


def diaspora_message_handler(xpath):
    """
    Decorator which registers a handler to handle messages from the D* netork,
    selected if the incoming messages matches <xpath>.
    """
    def _inner(cls):
        HANDLERS[xpath] = cls
        return cls
    return _inner


def process_incoming_message(payload, c_from, u_to):
    """
    Decide which type of message this is, and call the correct handler.
    """
    xml = payload.lstrip()
    current_app.logger.debug(
        u'Message received from {0} for {1}\n{2}'.format(
            c_from.id, u_to.id if u_to else '(none)', xml
        )
    )
    doc = etree.fromstring(xml)
    for xpath, handler in HANDLERS.items():
        if doc.xpath(xpath):
            return handler.receive(doc, c_from, u_to)
    raise Exception("No handler registered", payload)


class MessageHandlerBase:
    """
    Generic base class for base handlers.
    """

    @classmethod
    def _build(cls, u_from, c_to, **kwargs):
        """
        Generate an XML message to send to a remote node.
        """
        diasp = DiasporaContact.get_for_contact(u_from.contact)
        fn = kwargs.pop('fn', cls.generate)
        xml = fn(u_from, c_to, **kwargs)
        m = DiasporaMessageBuilder(xml, diasp.username, u_from._unlocked_key)
        return m

    @classmethod
    def send(cls, u_from, c_to, **kwargs):
        """
        Send a message from <u_from> to <c_to>.
        """
        m = cls._build(u_from, c_to, **kwargs)
        url = '{0}receive/users/{1}'.format(
            c_to.diasp.server, c_to.diasp.guid)
        current_app.logger.debug(u'posting {0} to {1}'.format(
            etree.tostring(m.message),
            url
        ))
        resp = m.post(url, RSA.importKey(c_to.public_key))
        return resp

    @classmethod
    def send_public(cls, u_from, c_to, **kwargs):
        """
        Send a message from <u_from> to the remote server that <c_to> is on,
        as a public message.
        """
        m = cls._build(u_from, None, **kwargs)
        url = '{0}receive/public'.format(c_to.diasp.server)
        current_app.logger.debug(u'posting {0} to {1}'.format(
            etree.tostring(m.message),
            url
        ))
        resp = m.post(url, None)
        return resp

    @classmethod
    def struct_to_xml(cls, node, struct):
        """
        Turn a list of dicts into XML nodes with tag names taken from the dict
        keys and element text taken from dict values. This is a list of dicts
        so that the XML nodes can be ordered in the XML output.
        """
        for obj in struct:
            for k, v in obj.items():
                etree.SubElement(node, k).text = v

    @classmethod
    def as_dict(cls, xml):
        """
        Turn the children of node <xml> into a dict, keyed by tag name. This
        is only a shallow conversation - child nodes are not recursively
        processed.
        """
        node = xml[0][0]
        return dict((e.tag, e.text) for e in node)

    @classmethod
    def format_dt(cls, dt):
        """
        Format a datetime in the way that D* nodes expect.
        """
        return ensure_timezone(dt).astimezone(tzutc()).strftime(
            '%Y-%m-%d %H:%M:%S %Z'
        )


class SignableMixin:
    """
    Mix-in to handle 'signing' and verifying blocks of XML.
    """

    @classmethod
    def generate_signature(cls, u_from, node):
        """
        Sign a given node with <u_from>'s key.
        """
        sig_contents = ';'.join([
            e.text for e in node
            if e.text is not None
            and not e.tag.endswith('_signature')
        ])
        sig_hash = SHA256.new(sig_contents.encode("utf-8"))
        cipher = PKCSSign.new(u_from._unlocked_key)
        return b64encode(cipher.sign(sig_hash))

    @classmethod
    def valid_signature(cls, contact, signature, node):
        """
        Validate <signature> convirms that <contact> signed the node <node>.
        """
        assert(contact)
        assert(signature)
        assert(node is not None)
        sig_contents = ';'.join([
            e.text for e in node
            if e.text is not None
            and not e.tag.endswith('_signature')
        ])
        signature = b64decode(signature)
        sig_hash = SHA256.new(sig_contents.encode("utf-8"))
        cipher = PKCSSign.new(RSA.importKey(contact.public_key))
        return cipher.verify(sig_hash, signature)


class TagMixin:
    """
    Mix-in for messages that receive tag strings (#word) and need to parse
    them into Tag objects.
    """
    tag_re = re_compile('#[a-zA-z0-9_]+')

    @classmethod
    def find_tags(cls, text):
        """
        Parse <text> for things that look like tags and return matching Tag
        objects.
        """
        tl = ' '.join(m.group(0)[1:] for m in cls.tag_re.finditer(text))
        return Tag.parse_line(tl, create=True)


@diaspora_message_handler('/XML/post/request')
class Subscribe(MessageHandlerBase):
    """
    Notification of subscription creation.
    """

    @classmethod
    def receive(cls, xml, c_from, u_to):
        """
        Contact <c_from> has subcribed to <u_to>.
        """
        data = cls.as_dict(xml)
        assert(data['sender_handle'] == c_from.diasp.username)
        if not c_from.subscribed_to(u_to.contact):
            c_from.subscribe(u_to.contact)

    @classmethod
    def generate(cls, u_from, c_to):
        """
        User <u_from> wishes to subscribe to <c_to>.
        """
        req = etree.Element("request")
        cls.struct_to_xml(req, [
            {'sender_handle': u_from.contact.diasp.username},
            {'recipient_handle': c_to.diasp.username}
        ])
        return req


@diaspora_message_handler('/XML/post/profile')
class Profile(TagMixin, MessageHandlerBase):
    """
    Notification that a profile has changed.
    """

    @classmethod
    def receive(cls, xml, c_from, u_to):
        """
        Contact <c_from has updated their profile.
        """
        data = cls.as_dict(xml)
        assert(data['diaspora_handle'] == c_from.diasp.username)
        c_from.realname = " ".join(
            data.get(k, '') or '' for k in ('first_name', 'last_name')
        )
        c_from.bio = MimePart(
            text_preview=data.get('bio', '(bio)'),
            body=dumps(data).encode('utf-8'),
            type='application/x-pyaspora-diaspora-profile'
        )
        if 'image_url' in data:
            mp = import_url_as_mimepart(urljoin(
                c_from.diasp.server,
                data['image_url']
            ))
            mp.text_preview = u'(picture for {0})'.format(c_from.realname)
            c_from.avatar = mp
        else:
            c_from.avatar = None

        c_from.interests = cls.find_tags(data['tag_string'] or '')

        db.session.add(c_from)
        db.session.commit()

    @classmethod
    def generate(cls, u_from, c_to):
        """
        User <u_from> has updated their profile and wishes to let contact
        <c_to> know.
        """
        req = etree.Element("profile")
        name_parts = u_from.contact.realname.split()
        if len(name_parts) == 1:
            name_parts.append('')
        cls.struct_to_xml(req, [
            {'diaspora_handle': u_from.contact.diasp.username},
            {'first_name': name_parts[0]},
            {'last_name': ' '.join(name_parts[1:])},
            {'image_url': url_for(
                'contacts.avatar', contact_id=u_from.contact.id, _external=True
            )},
            {'birthday': None},
            {'gender': None},
            {'location': None},
            {'searchable': 'true'},
            {'nsfw': 'false'},
            {'tag_string': ' '.join(
                '#' + t.name for t in u_from.contact.interests
            )}
        ])
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
        cls.struct_to_xml(req, [
            {'post_guid': u_from.contact.diasp.guid},
            {'type': 'Person'},
            {'diaspora_handle': u_from.contact.diasp.username}
        ])
        return req


@diaspora_message_handler('/XML/post/status_message')
class PostMessage(TagMixin, MessageHandlerBase):
    """
    A top-level post.
    """
    @classmethod
    def receive(cls, xml, c_from, u_to):
        data = cls.as_dict(xml)
        if DiasporaPost.get_by_guid(data['guid']):
            return
        public = (data['public'] == 'true')
        assert(public or u_to)
        assert(data['diaspora_handle'] == c_from.diasp.username)
        created = datetime.strptime(data['created_at'], '%Y-%m-%d %H:%M:%S %Z')
        p = Post(author=c_from, created_at=created)
        msg = data.get('raw_message', None)
        if msg is None:
            msg = data.get('photo', None)
        if msg is None:
            msg = ''
        p.add_part(MimePart(
            type='text/x-markdown',
            body=msg.encode('utf-8'),
        ), order=0, inline=True)
        p.tags = cls.find_tags(msg)

        if 'poll' in data:
            pd = xml.xpath('//poll')[0]
            part = MimePart(
                type='application/x-diaspora-poll-question',
                body=pd.xpath('./question')[0].text.encode('utf-8')
            )
            part.diasp = DiasporaPart(guid=pd.xpath('./guid')[0].text)
            p.add_part(part, order=1, inline=True)
            for pos, answer in enumerate(pd.xpath('./poll_answer')):
                part = MimePart(
                    type='application/x-diaspora-poll-answer',
                    body=answer.xpath('./answer')[0].text.encode('utf-8')
                )
                part.diasp = DiasporaPart(guid=answer.xpath('./guid')[0].text)
                p.add_part(part, order=2+pos, inline=True)

        if public:
            p.share_with([c_from], show_on_wall=True)
        else:
            p.share_with([c_from])
            if u_to.contact.subscribed_to(c_from):
                p.share_with([u_to.contact])
        p.thread_modified()

        p.diasp = DiasporaPost(
            guid=data['guid'],
            type='public' if public else 'limited'
        )
        db.session.commit()

    @classmethod
    def generate(cls, u_from, c_to, post, text):
        diasp = DiasporaPost.get_for_post(post)
        req = etree.Element("status_message")
        cls.struct_to_xml(req, [
            {'raw_message': text},
            {'guid': diasp.guid},
            {'diaspora_handle': u_from.contact.diasp.username},
            {'public': 'false' if c_to else 'true'},
            {'created_at': cls.format_dt(post.created_at)}
        ])
        return req


@diaspora_message_handler('/XML/post/conversation')
class PrivateMessage(SignableMixin, TagMixin, MessageHandlerBase):
    """
    The start of a private conversation. This doesn't see much use in
    Pyaspora because there is nothing to stop a top-level Post being
    private.
    """
    @classmethod
    def receive(cls, xml, c_from, u_to):
        data = cls.as_dict(xml)
        if DiasporaPost.get_by_guid(data['guid']):
            return
        node = xml.xpath('//message')[0]
        msg = dict((e.tag, e.text) for e in node)
        assert(data['diaspora_handle'] == c_from.diasp.username)
        assert(msg['diaspora_handle'] == c_from.diasp.username)
        if not current_app.config.get('ALLOW_INSECURE_COMPAT', False):
            assert(cls.valid_signature(c_from, msg['author_signature'], node))
        assert(cls.valid_signature(
            c_from, msg['parent_author_signature'], node
        ))
        assert(data['guid'] == msg['parent_guid'])
        assert(data['guid'] == msg['conversation_guid'])

        created = datetime.strptime(data['created_at'], '%Y-%m-%d %H:%M:%S %Z')
        p = Post(author=c_from, created_at=created)
        part_tags = [t for t in ('subject', 'text') if t in data or t in msg]
        for order, tag in enumerate(part_tags):
            p.add_part(MimePart(
                type='text/x-markdown' if tag == 'text' else 'text/plain',
                body=(data.get(tag, None) or msg[tag]).encode('utf-8'),
            ), order=order, inline=True)
        p.tags = cls.find_tags(msg['text'])
        p.share_with([c_from])
        if u_to.contact.subscribed_to(c_from):
            p.share_with([u_to.contact])
        p.thread_modified()
        p.diasp = DiasporaPost(guid=data['guid'], type='private')
        db.session.add(p)
        db.session.commit()

    @classmethod
    def generate(cls, u_from, c_to, post, text):
        req = etree.Element("conversation")
        diasp = DiasporaPost.get_for_post(post)
        cls.struct_to_xml(req, [
            {'guid': diasp.guid},
            {'subject': '(no subject)'},
            {'created_at': cls.format_dt(post.created_at)}
        ])
        msg = etree.SubElement(req, "message")
        cls.struct_to_xml(msg, [
            {'guid': diasp.guid + '-1'},
            {'parent_guid': diasp.guid},
            {'text': text},
            {'created_at': cls.format_dt(post.created_at)},
            {'diaspora_handle': u_from.contact.diasp.username},
            {'conversation_guid': diasp.guid}
        ])
        etree.SubElement(msg, "parent_author_signature").text = \
            cls.generate_signature(u_from, msg)
        etree.SubElement(msg, "author_signature").text = \
            cls.generate_signature(u_from, msg)
        cls.struct_to_xml(req, [
            {'diaspora_handle': u_from.contact.diasp.username},
            {'participant_handles': ';'.join(
                s.contact.diasp.username for s in post.shares
                if s.contact.diasp
            )}
        ])

        return req


@diaspora_message_handler('/XML/post/participation/target_type[text()="Post"]')
class PostParticipation(SignableMixin, MessageHandlerBase):
    """
    Somewhat like a Share in Pyaspora, it indicates that someone is
    participating in a conversation on a post (not a PM). However this can be
    easily inferred by virtue of receiving a post by the new author!
    """
    @classmethod
    def receive(cls, xml, c_from, u_to):
        # Not sure what these do, but they don't seem to be necessary, so do
        # nothing - like Shares?
        data = cls.as_dict(xml)
        post = DiasporaPost.get_by_guid(data['parent_guid'])
        if not post:
            raise TryLater()
        post = post.post  # Underlying Post object
        if post.is_public():
            return

        participant = DiasporaContact.get_by_username(
            data['diaspora_handle'], True, False
        )
        assert(participant)
        node = xml[0][0]
        if 'parent_author_signature' in data:
            assert(
                cls.valid_signature(
                    post.author, data['parent_author_signature'], node
                )
            )
            if not current_app.config.get('ALLOW_INSECURE_COMPAT', False):
                assert(
                    cls.valid_signature(
                        participant, data['author_signature'], node
                    )
                )
        else:
            assert(
                cls.valid_signature(
                    participant, data['author_signature'], node
                )
            )

        if not post.shared_with(participant.contact):
            post.share_with([participant.contact], remote=False)


@diaspora_message_handler('/XML/post/comment')
class SubPost(SignableMixin, TagMixin, MessageHandlerBase):
    """
    A comment on a top-level post. In Pyaspora these are posts in their own
    right, but the federation protocol treats these differently.
    """
    @classmethod
    def receive(cls, xml, c_from, u_to):
        data = cls.as_dict(xml)
        if DiasporaPost.get_by_guid(data['guid']):
            return
        author = DiasporaContact.get_by_username(
            data['diaspora_handle'], True, False
        )
        assert(author)
        author = author.contact
        parent = DiasporaPost.get_by_guid(data['parent_guid'])

        # Which post is this in reply to?
        if parent:
            parent = parent.post
        else:
            raise TryLater()

        if u_to:
            assert(parent.shared_with(c_from))
        node = xml[0][0]
        if 'parent_author_signature' in data:
            assert(
                cls.valid_signature(
                    parent.root().author, data['parent_author_signature'], node
                )
            )
            if not current_app.config.get('ALLOW_INSECURE_COMPAT', False):
                assert(
                    cls.valid_signature(author, data['author_signature'], node)
                )
        else:
            assert(cls.valid_signature(author, data['author_signature'], node))

        p = Post(author=author, parent=parent)
        p.add_part(MimePart(
            type='text/x-markdown',
            body=data['text'].encode('utf-8'),
        ), order=0, inline=True)
        p.tags = cls.find_tags(data['text'])
        if u_to:
            p.share_with([p.author])
            if parent.shared_with(u_to.contact):
                p.share_with([u_to.contact])
        else:
            p.share_with([p.author], show_on_wall=True)
        if p.author.id != c_from.id:
            p.share_with([c_from])

        p.thread_modified()

        p.diasp = DiasporaPost(
            guid=data['guid'],
            type='limited' if u_to else 'public'
        )
        db.session.add(p)
        db.session.commit()

        if not(u_to) or (p.parent.author_id == u_to.contact.id):
            # If the parent has signed this then it must have already been
            # via the hub.
            if 'parent_author_signature' not in data:
                cls.forward(u_to, p, node)

    @classmethod
    def generate(cls, u_from, c_to, post, text):
        req = etree.Element('comment')
        diasp = DiasporaPost.get_for_post(post)
        p_diasp = DiasporaPost.get_for_post(post.root())

        cls.struct_to_xml(req, [
            {'guid': diasp.guid},
            {'parent_guid': p_diasp.guid},
            {'text': text},
            {'diaspora_handle': post.author.diasp.username}
        ])
        etree.SubElement(req, "author_signature").text = \
            cls.generate_signature(u_from, req)
        if p_diasp.post.author.id == u_from.id:
            etree.SubElement(req, "parent_author_signature").text = \
                cls.generate_signature(u_from, req)
        return req

    @classmethod
    def forward(cls, u_from, post, node):
        parent_sig = [n for n in node if n.tag == 'parent_author_signature']
        assert(not parent_sig)
        if u_from:
            etree.SubElement(node, "parent_author_signature").text = \
                cls.generate_signature(u_from, node)

        def _builder(u_from, c_to, n):
            return n
        already_shared = set([s.contact_id for s in post.shares])
        targets = [s.contact for s in post.parent.shares
                   if s.contact_id not in already_shared]
        post.share_with(targets)
        is_public = (post.root().is_public())
        if is_public:
            targets += list(post.author.followers())
        targets = [c for c in targets if not c.user]
        for target in targets:
            if is_public:
                cls.send_public(None, target, n=node, fn=_builder)
            else:
                cls.send(u_from, target, n=node, fn=_builder)


@diaspora_message_handler('/XML/post/message')
class SubPM(SignableMixin, TagMixin, MessageHandlerBase):
    """
    A response to a private message thread.
    """
    @classmethod
    def receive(cls, xml, c_from, u_to):
        data = cls.as_dict(xml)
        if DiasporaPost.get_by_guid(data['guid']):
            return
        author = DiasporaContact.get_by_username(
            data['diaspora_handle'], True, False
        )
        assert(author)
        author = author.contact
        parent = DiasporaPost.get_by_guid(data['parent_guid']).post
        if not parent:
            raise TryLater()
        assert(parent.shared_with(c_from))
        assert(parent.shared_with(u_to))
        node = xml[0][0]
        if 'parent_author_signature' in data:
            assert(cls.valid_signature(
                parent.author, data['parent_author_signature'], node
            ))
            if not current_app.config.get('ALLOW_INSECURE_COMPAT', False):
                assert(
                    cls.valid_signature(author, data['author_signature'], node)
                )
        else:
            assert(cls.valid_signature(author, data['author_signature'], node))

        created = datetime.strptime(data['created_at'], '%Y-%m-%d %H:%M:%S %Z')
        p = Post(author=author, created_at=created, parent=parent)
        p.add_part(MimePart(
            type='text/x-markdown',
            body=data['text'].encode('utf-8'),
        ), order=0, inline=True)
        p.tags = cls.find_tags(data['text'])
        p.share_with([s.contact for s in p.root().shares])
        p.thread_modified()
        p.diasp = DiasporaPost(guid=data['guid'], type='private')
        db.session.add(p)
        db.session.commit()

        if not(u_to) or (p.parent.author_id == u_to.contact.id):
            # If the parent has signed this then it must have already been
            # via the hub.
            if 'parent_author_signature' not in data:
                cls.forward(u_to, p, node)

    @classmethod
    def generate(cls, u_from, c_to, post, text):
        req = etree.Element('message')
        diasp = DiasporaPost.get_for_post(post)
        p_diasp = DiasporaPost.get_for_post(post.root())

        cls.struct_to_xml(req, [
            {'guid': diasp.guid},
            {'parent_guid': p_diasp.guid},
            {'text': text},
            {'created_at': cls.format_dt(post.created_at)},
            {'diaspora_handle': post.author.diasp.username},
            {'conversation_guid': p_diasp.guid}
        ])
        etree.SubElement(req, "author_signature").text = \
            cls.generate_signature(u_from, req)
        if p_diasp.post.author.id == u_from.id:
            etree.SubElement(req, "parent_author_signature").text = \
                cls.generate_signature(u_from, req)
        return req

    @classmethod
    def forward(cls, u_from, post, node):
        parent_sig = [n for n in node if n.tag == 'parent_author_signature']
        assert(not parent_sig)
        if u_from:
            etree.SubElement(node, "parent_author_signature").text = \
                cls.generate_signature(u_from, node)

        def _builder(u_from, c_to, n):
            return n
        already_shared = set([s.contact_id for s in post.shares])
        targets = [s.contact for s in post.parent.shares
                   if s.contact_id not in already_shared]
        post.share_with(targets)
        targets = [c for c in targets if not c.user]
        for target in targets:
            cls.send(u_from, target, n=node, fn=_builder)


@diaspora_message_handler('/XML/post/like')
class Like(MessageHandlerBase):
    """
    A post being "liked". Pyaspora doesn't do likes, this is ignored.
    """
    @classmethod
    def receive(cls, xml, c_from, u_to):
        # Pyaspora does not support likes
        pass


@diaspora_message_handler('/XML/post/relayable_retraction')
@diaspora_message_handler('/XML/post/signed_retraction')
class Retraction(MessageHandlerBase):
    """
    An attempt to delete a previously-sent post, comment or PM. Pyaspora
    doesn't currently support this.
    """
    @classmethod
    def receive(cls, xml, c_from, u_to):
        # Pyaspora does not support deleting posts/PMs
        pass


@diaspora_message_handler('/XML/post/photo')
class Photo(MessageHandlerBase):
    """
    An image attached to a top-level post. This message usually comes through
    just after the notification of the post.
    """
    @classmethod
    def receive(cls, xml, c_from, u_to):
        data = cls.as_dict(xml)
        assert(data['diaspora_handle'] == c_from.diasp.username)
        target_guid = data.get('status_message_guid', data['guid'])
        parent = DiasporaPost.get_by_guid(target_guid)

        if parent:
            parent = parent.post
        else:
            raise TryLater()

        assert(parent.shared_with(c_from))

        # Check if already received here
        for part in parent.parts:
            dp = part.mime_part.diasp
            if dp and dp.guid == data['guid']:
                return

        photo_url = urljoin(
            data['remote_photo_path'], data['remote_photo_name']
        )
        resp = urlopen(photo_url, timeout=10)
        mime = resp.info().get('Content-Type')
        part = MimePart(
            type=mime,
            body=resp.read(),
            text_preview='(picture)'
        )
        parent.add_part(
            part,
            order=0,
            inline=bool(mime.startswith('image/'))
        )
        parent.thread_modified()
        db.session.add(parent)
        db.session.add(DiasporaPart(part=part, guid=data['guid']))
        db.session.commit()


@diaspora_message_handler('/XML/post/reshare')
class Reshare(MessageHandlerBase):
    """
    An existing post is being reshared.
    """
    @classmethod
    def receive(cls, xml, c_from, u_to):
        data = cls.as_dict(xml)
        shared = DiasporaPost.get_by_guid(data['root_guid'])
        if not shared:
            author = DiasporaContact.get_by_username(
                data['root_diaspora_id'], True, True
            )
            if not author:
                raise TryLater()
            author.import_public_posts()
            shared = DiasporaPost.get_by_guid(data['root_guid'])

        if not shared:
            current_app.logger.warning(
                'Could not find post being reshared (with GUID {0})'.format(
                    data['root_guid']
                )
            )
            raise TryLater()
        shared = shared.post
        created = datetime.strptime(data['created_at'], '%Y-%m-%d %H:%M:%S %Z')
        post = Post(author=c_from, created_at=created)
        share_part = MimePart(
            type='application/x-pyaspora-share',
            body=dumps({
                'post': {'id': shared.id},
                'author': {
                    'id': shared.author_id,
                    'name': shared.author.realname,
                }
            }).encode('utf-8'),
            text_preview=u"shared {0}'s post".format(shared.author.realname)
        )
        post.add_part(share_part, order=0, inline=True)
        order = 0
        for part in shared.parts:
            if part.mime_part.type != 'application/x-pyaspora-share':
                order += 1
                post.add_part(part.mime_part, inline=part.inline, order=order)
        if not post.tags:
            post.tags = shared.tags
        if u_to:
            post.share_with([c_from])
            if u_to.contact.subscribed_to(c_from):
                p.share_with([u_to.contact])
        else:
            post.share_with([c_from], show_on_wall=True)
        post.thread_modified()

        post.diasp = DiasporaPost(
            guid=data['guid'],
            type='limited' if u_to else 'public'
        )
        db.session.add(post)
        db.session.commit()

    @classmethod
    def generate(cls, u_from, c_to, post, reshare):
        req = etree.Element('reshare')
        diasp = DiasporaPost.get_for_post(post)
        r_diasp = DiasporaPost.get_for_post(reshare)

        cls.struct_to_xml(req, [
            {'root_diaspora_id': reshare.author.diasp.username},
            {'root_guid': r_diasp.guid},
            {'guid': diasp.guid},
            {'diaspora_handle': post.author.diasp.username},
            {'public': 'true'},
            {'created_at': cls.format_dt(reshare.created_at)}
        ])
        return req


@diaspora_message_handler('/XML/post/poll_participation')
class PollParticipation(MessageHandlerBase, SignableMixin):
    """
    A vote in a poll
    """
    @classmethod
    def receive(cls, xml, c_from, u_to):
        data = cls.as_dict(xml)
        if DiasporaPost.get_by_guid(data['guid']):
            return
        author = DiasporaContact.get_by_username(
            data['diaspora_handle'], True, False
        )
        assert(author)
        author = author.contact
        poll_part = DiasporaPart.get_by_guid(data['parent_guid'])
        if not poll_part:
            raise TryLater()
        posts = dict((p.post.id, p.post) for p in poll_part.part.posts)
        if not posts:
            raise TryLater()

        answer_part = DiasporaPart.get_by_guid(data['poll_answer_guid'])
        assert answer_part, 'Poll participation must have stored answer'

        new_part = MimePart(
            type='application/x-diaspora-poll-participation',
            body=dumps({
                'poll_guid': data['parent_guid'],
                'answer_guid': data['poll_answer_guid'],
                'answer_text': answer_part.part.body.decode('utf-8')
            })
        )

        node = xml[0][0]
        assert(cls.valid_signature(author, data['author_signature'], node))

        saved = []
        for parent in posts.values():
            # FIXME: we should validate parent_author_signature against, err
            # the right post.
            if u_to and not parent.shared_with(c_from):
                continue
            p = Post(author=author, parent=parent)
            saved.append(p)
            p.add_part(new_part, order=0, inline=True)

            if u_to:
                p.share_with([p.author])
                if parent.shared_with(u_to.contact):
                    p.share_with([u_to.contact])
            else:
                p.share_with([p.author], show_on_wall=True)
            if p.author.id != c_from.id:
                p.share_with([c_from])

            p.thread_modified()

            p.diasp = DiasporaPost(
                guid=data['guid'],
                type='limited' if u_to else 'public'
            )
            db.session.add(p)

        db.session.commit()

        for p in saved:
            if not(u_to) or (p.parent.author_id == u_to.contact.id):
                # If the parent has signed this then it must have already been
                # via the hub.
                if 'parent_author_signature' not in data:
                    cls.forward(u_to, p, node)


@diaspora_message_handler('/XML/post/account_deletion')
class AccountDeletion(MessageHandlerBase):
    """
    An account is being deleted
    """
    @classmethod
    def receive(cls, xml, c_from, u_to):
        data = cls.as_dict(xml)

        participant = DiasporaContact.get_by_username(
            data['diaspora_handle'], False
        )
        if not participant:
            return

        participant.contact.bio = MimePart(
            text_preview="This account has been deleted.",
            body="This account has been deleted.",
            type="text/plain"
        )
        db.session.add(participant)
        db.session.query(Subscription).filter(
            Subscription.to_contact == participant.contact
        ).delete()
        db.session.commit()
