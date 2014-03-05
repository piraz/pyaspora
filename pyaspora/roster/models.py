from __future__ import absolute_import

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import and_

from pyaspora.database import db
from pyaspora.utils.models import TagParseMixin


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
    from_id = Column(Integer, ForeignKey('contacts.id'),
                     primary_key=True)
    from_contact = relationship("Contact", backref="subscriptions",
                                foreign_keys=[from_id])
    to_id = Column(Integer, ForeignKey('contacts.id'),
                   primary_key=True)
    to_contact = relationship("Contact", backref="subscribers",
                              foreign_keys=[to_id])

    group_id = Column(Integer, ForeignKey('subscription_groups.id'),
                      nullable=True)

    class Queries:
        @classmethod
        def user_subs_for_contacts(cls, user, contact_ids):
            return and_(
                Subscription.to_id.in_(contact_ids),
                Subscription.from_id == user.contact.id
            )

    @classmethod
    def create(cls, from_contact, to_contact):
        """
        Create a new subscription, where <user> subscribes to <contact> with
        type <subtype>.  The group name <group> will be used, and the group
        will be created if it doesn't already exist. A privacy level of
        <private> will be assigned to the Subscription.
        """
        sub = cls(
            from_contact=from_contact,
            to_contact=to_contact
        )
        db.session.add(sub)
        return sub


class SubscriptionTag(db.Model):
    __tablename__ = "subscription_tags"
    subscription_id = Column(Integer, ForeignKey('subscriptions.from_id'),
                             primary_key=True)
    subscription = relationship("Subscription")
    group_id = Column(Integer, ForeignKey('subscription_groups.id'),
                      primary_key=True)
    group = relationship("SubscriptionGroup")


class SubscriptionGroup(TagParseMixin, db.Model):
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
    subscriptions = relationship(
        'Subscription',
        secondary='subscription_tags',
        backref='groups'
    )
    user = relationship('User', backref='groups')

    @classmethod
    def get(cls, groupid):
        """
        Given a primary key ID, return the SubscriptionGroup. Returns None if
        the group doesn't exist.
        """
        return db.session.query(cls).get(groupid)

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

    @classmethod
    def get_by_name(cls, name, user, create=True):
        """
        Returns the group named <group> owned by User <user>. If the group
        does not exist and <create> is False, None will be returned. If
        <create> is True, a new SubscriptionGroup will be created and returned.
        """
        if not cls.name_is_valid(name):
            return

        group = db.session.query(cls).filter(and_(
            cls.name == name,
            cls.user == user
        )).first()
        if create and not group:
            group = cls(name=name, user=user)
            db.session.add(group)

        return group
