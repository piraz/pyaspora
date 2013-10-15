import random  # salt generation for hashing
import uuid  # to construct the user GUIDs

from Crypto.PublicKey import RSA
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship
from sqlalchemy.schema import Column, ForeignKey, UniqueConstraint
from sqlalchemy.sql import and_
from sqlalchemy.sql.expression import func
from sqlalchemy.types import Boolean, DateTime, Integer, LargeBinary, String

import pyaspora.renderer

from pyaspora.tools.sqlalchemy import metadata, session

Base = declarative_base(metadata=metadata)


class Subscription(Base):
    """
    A one-way 'friendship' between a user and a contact (that could be local
    or external).  This class doesn't store the user explicitly, but via a
    SubscriptionGroup.

    Fields:
        group - the SubscriptionGroup this Subscription is part of
        group_id - the database primary key of the above
        contact - the Contact the user is subscribed to
        contact_id - the database primary key of the above
        type - the nature of this subscription (eg. "friend", "feed")
    """

    __tablename__ = "subscriptions"
    group_id = Column(Integer, ForeignKey('subscription_groups.id'), primary_key=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'), primary_key=True)
    type = Column(String, nullable=False)

    @classmethod
    def create(cls, user, contact, group, subtype='friend'):
        """
        Create a new subscription, where <user> subscribes to <contact> with
        type <subtype>.  The group name <group> will be used, and the group
        will be created if it doesn't already exist. A privacy level of
        <private> will be assigned to the Subscription.
        """
        dbgroup = SubscriptionGroup.get_by_name(user=user, group=group, create=True)
        sub = cls(group=dbgroup, contact_id=contact.id, type=subtype)
        session.add(sub)
        return sub


class SubscriptionGroup(Base):
    """
    A group of subscriptions ("friendships") by category, rather like
    "Circles" in G+.

    Fields:
        id - an integer identifier uniquely identifying this group in the node
        user - the User this group belongs to
        user_id - the database primary key of the above
        name - the category name. Must be unique for the user
        subscriptions - a list of Subscriptions that art part of this group
    """

    __tablename__ = "subscription_groups"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    __table_args__ = (
        UniqueConstraint(user_id, name),
    )
    subscriptions = relationship('Subscription', backref='group')

    @classmethod
    def get(cls, groupid):
        """
        Given a primary key ID, return the SubscriptionGroup. Returns None if
        the group doesn't exist.
        """
        return session.query(cls).get(groupid)

    @classmethod
    def get_by_name(cls, user, group, create=False):
        """
        Returns the group named <group> owned by User <user>. If the group
        does not exist and <create> is False, None will be returned. If
        <create> is True, a new SubscriptionGroup will be created and returned.
        """
        dbgroup = session.query(cls).filter(and_(cls.name == group, cls.user_id == user.id)). \
            first()
        if create and not dbgroup:
            dbgroup = cls(user=user, name=group)
            session.add(dbgroup)
        return dbgroup

    def has_contact(self, contact):
        for sub in self.subscriptions:
            if sub.contact_id == contact.id:
                return sub
        return None

    def add_contact(self, contact, subtype):
        if self.has_contact(contact):
            return
        sub = Subscription(contact=contact, group=self, type=subtype)
        session.add(sub)


class User(Base):
    """
    A local user who is based on this node, and who can log in, view their
    feed and manage their account. Users are associated with a Contact which
    is their external representation - thus, all Users must have a contact.

    Fields:
        id - an integer identifier uniquely identifying this group in the node
        email - the user's email address. Must be unique across the node.
        guid - the user's GUID. Must be unique across the node.
        private_key - an encrypted private key for the user
        public_key - the public key for the above private key
        contact - the Contact this user is associated with
        contact_id - the database primary key for the above
        activated - None until the user activates their account by email.
                    Afterwards a DateTime of activation.
        groups - a list of SubscriptionGroups the user owns
    """

    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    guid = Column(String, unique=True, nullable=False, default=lambda: uuid.uuid4().hex)
    private_key = Column(String, nullable=False)
    contact_id = Column(Integer, ForeignKey('contacts.id'), nullable=False)
    activated = Column(DateTime, nullable=True, default=None)
    groups = relationship('SubscriptionGroup', backref='user')
    message_queue = relationship('MessageQueue', backref='local')

    @classmethod
    def get(cls, userid):
        """
        Get a user by primary key ID. Returns None if the user cannot be found.
        """
        return session.query(cls).get(userid)

    @classmethod
    def get_by_guid(cls, guid):
        """
        Fetches a user with GUID <guid>.
        """
        return session.query(cls).filter(cls.guid == guid).first()

    @classmethod
    def get_unactivated(cls, guid):
        """
        Fetches an unactivated user with GUID <guid>.
        """
        contact = cls.get_by_guid(guid)
        if contact and not contact.activated:
            return None
        return contact

    @classmethod
    def get_by_email(cls, email):
        """
        Fetches a user by email address.
        """
        return session.query(cls).filter(cls.email == email).first()

    def __init__(self, contact=None):
        """
        Creates a new user, creating a new Contact for the user if none is
        supplied. The contact is then associated with the newly created User.
        """
        Base.__init__(self)
        if not contact:
            contact = Contact()
        self.contact = contact
        session.add(self)

    def activate(self):
        """
        Mark the user as having activated successfully.
        """
        if not self.activated:
            self.activated = func.now()

    def unlock_key_with_password(self, password):
        """
        Check if the user's password is <password>, returning a private key is
        possible, or None if the private key cannot be decrypted.
        """
        try:
            return RSA.importKey(self.private_key, passphrase=password)
        except (ValueError, IndexError, TypeError):
            return None

    def subscribed_to(self, contact, subtype=None):
        """
        Check if the user is subscribed to <contact> and return the
        Subscription object if so.  Can be constrained to check for only
        subscriptions of type <subtype>; if not supplied it will return the
        first Subscription to the contact of any type. If the user has no
        subscriptions to Contact then None will be returned.
        """
        sub = session.query(Subscription).join(SubscriptionGroup). \
            filter(and_(SubscriptionGroup.user_id == self.id,
                   Subscription.contact_id == contact.id))
        if subtype:
            sub = sub.filter(Subscription.type == subtype)
        sub = sub.first()
        return sub

    def friends(self, subtype=None):
        """
        Returns a list of Subscriptions (of type <subtype>, or all types if
        none supplied), de-duped by Contact (a Contact may exist in several
        SubscriptionGroups, this will select one at random if so).
        """
        friends = []
        for group in self.groups:
            for sub in group.subscriptions:
                if not(subtype) or sub.type == subtype:
                    if sub.contact not in friends:
                        friends.append(sub.contact)
        return friends

    def generate_keypair(self, passphrase):
        """
        Generate a 2048-bit RSA key. The key will be stored in the User object. The private key
        will be protected with password <passphrase>, which is usually the user password.
        """
        RSAkey = RSA.generate(2048)
        self.private_key = RSAkey.exportKey(format='PEM', pkcs=1, passphrase=passphrase).decode("ascii")
        self.contact.public_key = RSAkey.publickey().exportKey(format='PEM', pkcs=1).decode("ascii")


class Share(Base):
    """
    Represents a Post being displayed to a Contact, for example in their feed or on their wall.

    Fields:
        contact - the Contact the Post is being displayed to
        contact_id - the database primary key of the above
        post - the Post that is being shared with <contact>
        post_id - the database primary key of the above
        public - whether the post is shown on the user's public wall
        shared_at - the DateTime the Post was shared with the Contact (that is, the Share creation date)
    """
    __tablename__ = 'shares'
    contact_id = Column(Integer, ForeignKey('contacts.id'), primary_key=True)
    post_id = Column(Integer, ForeignKey('posts.id'), primary_key=True)
    public = Column(Boolean, nullable=False)
    shared_at  = Column(DateTime, nullable=False, default=func.now())


class Contact(Base):
    """
    A person or entity that can be befriended, shared-with and the like. They may be a local User
    or they may be an entity on a remote note, merely cached here.

    Fields:
        id - an integer identifier uniquely identifying this group in the node
        username - the "user@node" address of the user
        realname - the user's "real" name (how they wish to be known)
        avatar - a displayable MIME part that represents the user, typically a photo
        user - the User that this Contact is part of. For all non-local Contacts this is None
        posts - a list of Posts that the user has authored. May be incomplete for non-local users.
        feed - a list of Shares that is on this Contact's feed/wall. May be incomplete for non-local users.
        subscriptions - a list of Subscriptions for Users who are subscribed to this Contact
    """
    __tablename__ = 'contacts'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    realname = Column(String, nullable=False)
    bio_id = Column(Integer, ForeignKey("mime_parts.id"), nullable=True)
    avatar_id = Column(Integer, ForeignKey("mime_parts.id"), nullable=True)
    public_key = Column(String, nullable=False)
    user = relationship("User", single_parent=True, backref='contact', uselist=False)
    posts = relationship("Post", backref='author')
    feed = relationship("Share", backref="contact", order_by='Share.shared_at')
    subscriptions = relationship("Subscription", backref="contact")
    avatar = relationship("MimePart", foreign_keys=[avatar_id], primaryjoin='Contact.avatar_id==MimePart.id')
    bio = relationship("MimePart", foreign_keys=[bio_id], primaryjoin='Contact.bio_id==MimePart.id')

    @classmethod
    def get(cls, contactid):
        """
        Get a contact by primary key ID. None is returned if the Contact doesn't exist.
        """
        return session.query(cls).get(contactid)

    @classmethod
    def get_by_username(cls, username, try_import=False):
        """
        Get a Contact by "user@node" address. Returns None if the <username> is not known on
        this node.
        """
        contact = session.query(cls).filter(cls.username == username).first()
        if try_import and not contact:
            import pyaspora.diaspora
            contact = pyaspora.diaspora.import_contact(username)
            session.add(contact)
        return contact

    def subscribe(self, user, group='All', subtype='friend'):
        """
        Subscribe User <user> _to_ this Contact, onto <user>'s group named <group> with subscription
        type <subtype> and PrivacyLevel <privacy>.
        """
        sub = Subscription.create(user, self, group=group, subtype=subtype)
        session.add(sub)
        if not self.user:
            # FIXME send req via diasp
            pass

    def unsubscribe(self, user):
        """
        Remove this Contact from User <user>'s list of subscriptions.
        """
        subs = session.query(Subscription).join(SubscriptionGroup). \
                filter(and_(SubscriptionGroup.user_id == user.id,
                    Subscription.contact_id == self.id))
        if not self.user:
            # FIXME send req via diasp
            pass
        for sub in subs:
            session.delete(sub)


class PostPart(Base):
    """
    A link between a Post and a MIMEPart, specifying the order of parts in a Post. This class exists
    because one MIMEPart may be part of several Posts, for example where a Post is re-shared (which
    creates a new Post but with the same content (plus an additional comment).

    Fields:
        post - the Post this PostPart belongs to
        post_id - the database primary key for the above
        mime_part - the MimePart this PostPart links to
        mime_part_id - the database primary key for the above
        order - an integer specifying the sort order for the Post's PostParts, sorted ascending numerically
        inline - a boolean hint as to whether the part should be displayed inline or as an attachment
    """
    __tablename__ = 'post_parts'
    post_id = Column(Integer, ForeignKey('posts.id'), primary_key=True)
    mime_part_id = Column(Integer, ForeignKey('mime_parts.id'), primary_key=True)
    order = Column(Integer, nullable=False, default=0)
    inline = Column(Boolean, nullable=False, default=True)


class Post(Base):
    """
    A post (a collection of parts (text, images, etc) that together form an entry on a wall/feed etc.

    Fields:
        id - an integer identifier uniquely identifying this group in the node
        author - the Contact that authored the post
        author_id - the database primary key for the above
        parent - if this Post is a comment on another Post, this links to the parent Post. May be None.
        parent_id - the database primary key for the above
        shares - Shares of this Post (occurrences in feeds/on walls)
        parts - PostParts that this Post consists of (the Post contents)
        children - Posts that have this post as the parent
    """
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey('contacts.id'), nullable=False)
    parent_id = Column(Integer, ForeignKey('posts.id'), nullable=True, default=None)
    shares   = relationship('Share', backref='post')
    parts    = relationship('PostPart', backref='post', order_by=PostPart.order)
    children = relationship('Post', backref=backref('parent', remote_side=[id]))

    @classmethod
    def get(cls, postid):
        """
        Get a Post by primary key ID. Returns None if the Post doesn't exist.
        """
        return session.query(cls).get(postid)

    def has_permission_to_view(self, contact=None):
        """
        Whether the Contact <contact> is permitted to view this post.
        """
        # Is it visible to the world anywhere?
        is_public = session.query(Share).filter(and_(Share.public == True, Share.post == self)).first()
        if is_public:
            return True

        if not contact:
            return False

        # Can always view my own stuff
        if contact.id == self.author_id:
            return True
        # Check for other shares to the contact
        return self.shared_with(contact)

    def viewable_children(self, contact=None):
        """
        List of child posts that the Contact <contact> is permitted to view
        """
        return [child for child in self.children if child.permission_to_view(contact)]

    def add_part(self, mimepart, inline=False, order=1):
        """
        Adds MIMEPart <mimepart> to this Post, creating the linking PostPart (which is returned).
        """
        link = PostPart(post=self, mime_part=mimepart, inline=inline, order=order)
        session.add(link)
        return link

    def share_with(self, contacts, show_on_wall=False):
        """
        Share this Post with all the contacts in list <contacts>. This method doesn't share the
        post if the Contact already has this Post shared with them.
        """
        for contact in contacts:
            existing_share = session.query(Share).filter(and_(Share.post == self, Share.contact == contact)).first()
            if not existing_share:
                session.add(Share(contact=contact, post=self, public=show_on_wall))
                if not contact.user:
                    # FIXME share via diasp
                    pass

    def shared_with(self, contact):
        """
        Returns a boolean indicating whether this Post has already been shared with Contact <contact>.
        """
        share = session.query(Share).filter(and_(Share.contact == contact, Share.post == self)).first()
        return share


class MimePart(Base):
    """
    A piece of content (eg. text, HTML, image, video) that forms part of a Post.

    Fields:
        id - an integer identifier uniquely identifying this group in the node
        type - the MIME type (eg. "text/plain") of the body
        body - the raw content blob
        text_preview - plain text that can be displayed in lieu of content if the body cannot be displayed
        posts - a list of PostParts that this MimePart is used in
    """
    __tablename__ = 'mime_parts'
    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)
    body = Column(LargeBinary, nullable=False)
    text_preview = Column(String, nullable=False)
    posts = relationship('PostPart', backref='mime_part')

    def render_as(self, mime_type, inline=False):
        """
        Attempt to render (convert) this part into MIME type <mime_type>. Throws an exception if
        the conversion is not possible/not defined.
        """
        return pyaspora.renderer.Renderer.render(self, mime_type, inline)


class MessageQueue(Base):
    """
    Messages that have been received but that cannot be actioned until the User's public key
    has been unlocked (at which point they will be deleted).

    Fields:
        id - an integer identifier uniquely identifying the message in the queue
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
