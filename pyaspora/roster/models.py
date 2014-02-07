from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import and_

from pyaspora.database import db


class Subscription(db.Model):
    """
    A one-way 'friendship' between a user and a contact (that could be local
    or external).  This class doesn't store the user explicitly, but via a
    SubscriptionGroup.

    Fields:
        group - the SubscriptionGroup this Subscription is part of
        group_id - the database primary key of the above
        contact - the Contact the user is subscribed to
        contact_id - the database primary key of the above
    """

    __tablename__ = "subscriptions"
    group_id = Column(Integer, ForeignKey('subscription_groups.id'),
                      primary_key=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'),
                        primary_key=True, index=True)
    contact = relationship("Contact", backref="subscriptions")

    class Queries:
        @classmethod
        def user_shares_for_contacts(cls, user, contact_ids):
            return and_(
                Subscription.contact_id.in_(contact_ids),
                SubscriptionGroup.user_id == user.id
            )

    @classmethod
    def create(cls, user, contact, group):
        """
        Create a new subscription, where <user> subscribes to <contact> with
        type <subtype>.  The group name <group> will be used, and the group
        will be created if it doesn't already exist. A privacy level of
        <private> will be assigned to the Subscription.
        """
        dbgroup = SubscriptionGroup.get_by_name(user=user, group=group,
                                                create=True)
        sub = cls(group=dbgroup, contact_id=contact.id)
        db.session.add(sub)
        return sub


class SubscriptionGroup(db.Model):
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
    user_id = Column(Integer, ForeignKey("users.id"),
                     nullable=False, index=True)
    name = Column(String, nullable=False)
    __table_args__ = (
        UniqueConstraint(user_id, name),
    )
    subscriptions = relationship('Subscription', backref='group')
    user = relationship('User', backref='groups')

    @classmethod
    def get(cls, groupid):
        """
        Given a primary key ID, return the SubscriptionGroup. Returns None if
        the group doesn't exist.
        """
        return db.session.query(cls).get(groupid)

    @classmethod
    def get_by_name(cls, user, group, create=False):
        """
        Returns the group named <group> owned by User <user>. If the group
        does not exist and <create> is False, None will be returned. If
        <create> is True, a new SubscriptionGroup will be created and returned.
        """
        dbgroup = db.session.query(cls).filter(
            and_(cls.name == group, cls.user_id == user.id)).first()
        if create and not dbgroup:
            dbgroup = cls(user=user, name=group)
            db.session.add(dbgroup)
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
        db.session.add(sub)
