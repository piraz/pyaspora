from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import and_

from pyaspora.content.models import MimePart
from pyaspora.database import Base, db_session

class Contact(Base):
    """
    A person or entity that can be befriended, shared-with and the like. They may be a local User
    or they may be an entity on a remote note, merely cached here.

    Fields:
        id - an integer identifier uniquely identifying this group in the node
        realname - the user's "real" name (how they wish to be known)
        avatar - a displayable MIME part that represents the user, typically a photo
        user - the User that this Contact is part of. For all non-local Contacts this is None
        posts - a list of Posts that the user has authored. May be incomplete for non-local users.
        feed - a list of Shares that is on this Contact's feed/wall. May be incomplete for non-local users.
        subscriptions - a list of Subscriptions for Users who are subscribed to this Contact
    """
    __tablename__ = 'contacts'
    id = Column(Integer, primary_key=True)
    realname = Column(String, nullable=False)
    bio_id = Column(Integer, ForeignKey("mime_parts.id"), nullable=True)
    avatar_id = Column(Integer, ForeignKey("mime_parts.id"), nullable=True)
    public_key = Column(String, nullable=False)
    
    avatar = relationship("MimePart", foreign_keys=[avatar_id], primaryjoin='Contact.avatar_id==MimePart.id')
    bio = relationship("MimePart", foreign_keys=[bio_id], primaryjoin='Contact.bio_id==MimePart.id')

    @classmethod
    def get(cls, contactid):
        """
        Get a contact by primary key ID. None is returned if the Contact doesn't exist.
        """
        return db_session.query(cls).get(contactid)

    @classmethod
    def get_by_username(cls, username, try_import=False):
        """
        Get a Contact by "user@node" address. Returns None if the <username> is not known on
        this node.
        """
        contact = db_session.query(cls).filter(cls.username == username).first()
        if try_import and not contact:
            raise Exception("No such contact")
            #import pyaspora.diaspora
            #contact = pyaspora.diaspora.import_contact(username)
            #db_session.add(contact)
        return contact

    def subscribe(self, user, group='All', subtype='friend'):
        """
        Subscribe User <user> _to_ this Contact, onto <user>'s group named <group> with subscription
        type <subtype> and PrivacyLevel <privacy>.
        """
        from pyaspora.roster.models import Subscription
        sub = Subscription.create(user, self, group=group, subtype=subtype)
        db_session.add(sub)
        if not self.user:
            # FIXME send req via diasp
            pass

    def unsubscribe(self, user):
        """
        Remove this Contact from User <user>'s list of subscriptions.
        """
        from pyaspora.roster.models import Subscription, SubscriptionGroup
        subs = db_session.query(Subscription).join(SubscriptionGroup). \
                filter(and_(SubscriptionGroup.user_id == user.id,
                    Subscription.contact_id == self.id))
        if not self.user:
            # FIXME send req via diasp
            pass
        for sub in subs:
            db_session.delete(sub)
