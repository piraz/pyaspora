from __future__ import absolute_import

from json import dumps
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import joinedload, relationship
from sqlalchemy.sql import and_

from pyaspora import db
from pyaspora.content.models import MimePart


class Contact(db.Model):
    """
    A person or entity that can be befriended, shared-with and the like. They
    may be a local User or they may be an entity on a remote note, merely
    cached here.

    Fields:
        id - an integer identifier uniquely identifying this group in the node
        realname - the user's "real" name (how they wish to be known)
        avatar - a displayable MIME part that represents the user, typically a
                 photo
        user - the User that this Contact is part of. For all non-local
               Contacts this is None
        posts - a list of Posts that the user has authored. May be incomplete
                for non-local users.
        feed - a list of Shares that is on this Contact's feed/wall. May be
               incomplete for non-local users.
        subscriptions - a list of Subscriptions for Users who are subscribed
                        to this Contact
    """
    __tablename__ = 'contacts'
    id = Column(Integer, primary_key=True)
    realname = Column(String, nullable=False)
    bio_id = Column(Integer, ForeignKey("mime_parts.id"), nullable=True)
    avatar_id = Column(Integer, ForeignKey("mime_parts.id"), nullable=True)
    public_key = Column(String, nullable=False)

    avatar = relationship("MimePart", foreign_keys=[avatar_id],
                          primaryjoin='Contact.avatar_id==MimePart.id')
    bio = relationship("MimePart", foreign_keys=[bio_id],
                       primaryjoin='Contact.bio_id==MimePart.id')

    @classmethod
    def get(cls, contact_id, prefetch=True):
        """
        Get a contact by primary key ID. None is returned if the Contact
        doesn't exist. If prefetch is true (which it is by default) the
        contact's bio and avatar parts will be pre-fetched, along with any
        interests.
        """
        if prefetch:
            res = cls.get_many([contact_id])
            return res[0] if res else None
        else:
            return db.session.query(cls).get(contact_id)

    @classmethod
    def get_many(cls, contact_ids):
        """
        Fetch several contacts in one query, including the same pre-fetch
        items as Contact.get(). The contacts are returned in an unsorted
        order.
        """
        return db.session.query(cls). \
            options(
                joinedload(cls.avatar),
                joinedload(cls.bio),
                joinedload(cls.interests)
            ). \
            filter(cls.id.in_(contact_ids))

    def subscribe(self, contact):
        """
        Subscribe self to contact.
        """
        from pyaspora.diaspora.actions import Subscribe, Profile
        from pyaspora.roster.models import Subscription
        assert(self.user or contact.user)
        sub = Subscription(from_contact=self, to_contact=contact)
        db.session.add(sub)
        if not contact.user:
            Subscribe.send(self.user, contact)
            Profile.send(self.user, contact)
        self.notify_subscribe(contact)

    def unsubscribe(self, contact):
        """
        Remove this Contact from User <user>'s list of subscriptions.
        """
        from pyaspora.diaspora.actions import Unsubscribe
        from pyaspora.roster.models import Subscription
        subs = db.session.query(Subscription).filter(and_(
            Subscription.from_contact == self,
            Subscription.to_contact == contact
        ))
        for sub in subs:
            db.session.delete(sub)
        if not contact.user:
            Unsubscribe.send(self.user, contact)

    def notify_subscribe(self, contact):
        """
        Notify contact <contact> that they have a new follower (<self>),
        usually by placing an item in their feed. This is so the contact
        can see them and decide if they wish to follow them in return.
        The notice is also placed on <self>'s feed so they can know that
        they sent it.
        """
        from pyaspora.post.models import Post

        assert(self.user or contact.user)
        p = Post(author=self)
        db.session.add(p)

        p.add_part(
            order=0,
            inline=True,
            mime_part=MimePart(
                body=dumps({
                    'from': self.id,
                    'to': contact.id,
                }).encode('utf-8'),
                type='application/x-pyaspora-subscribe',
                text_preview='subscribed to {0}'.format(contact.realname)
            )
        )
        if self.user:
            p.share_with([self])
        if contact.user:
            p.share_with([contact])
        p.thread_modified()

    def subscribed_to(self, contact):
        """
        Check if the user is subscribed to <contact> and return the
        Subscription object if so. If the user has no subscriptions to Contact
        then None will be returned.
        """
        from pyaspora.roster.models import Subscription
        return db.session.query(Subscription). \
            filter(and_(
                Subscription.from_contact == self,
                Subscription.to_contact == contact,
            )).first()

    def friends(self):
        """
        Returns a list of Subscriptions that this contact made to others.
        """
        from pyaspora.roster.models import Subscription
        friends = db.session.query(Contact).join(Subscription.to_contact). \
            filter(Subscription.from_contact == self)
        return friends

    def followers(self):
        """
        Returns a list of Subscriptions that have expressed an interest in
        this contact.
        """
        from pyaspora.roster.models import Subscription
        friends = db.session.query(Contact).join(Subscription.from_contact). \
            filter(Subscription.to_contact == self)
        return friends
