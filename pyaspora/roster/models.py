"""
Database models relating to rosters (friend lists and subscriptions).
"""
from __future__ import absolute_import

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import and_

from pyaspora.database import db
from pyaspora.utils.models import TagParseMixin


class Subscription(db.Model):
    """
    A one-way 'friendship' between a contact and another contact (that could
    be local or external).

    Fields:
        from - the Contact that expressed an interest in "to"
        from_id - the database primary key of the above
        to - the Contact that <from> is interested in
        to_id - the database primary key of the above
    """

    __tablename__ = "subscriptions"
    from_id = Column(Integer, ForeignKey('contacts.id'),
                     primary_key=True)
    from_contact = relationship("Contact", backref="subscriptions",
                                foreign_keys=[from_id])
    to_id = Column(Integer, ForeignKey('contacts.id'),
                   primary_key=True, index=True)
    to_contact = relationship("Contact", backref="subscribers",
                              foreign_keys=[to_id])


class SubscriptionTag(db.Model):
    """
    A link between a SubscriptionGroup and a Subscription. One Subscription
    can feature in several groups at once.

    Fields:
        subscription_id - the Subscription this link is from
        group_id - the SubscriptionGroup this link is to
    """
    __tablename__ = "subscription_tags"
    group_id = Column(Integer, ForeignKey('subscription_groups.id'),
                      primary_key=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.from_id'),
                             primary_key=True, index=True)


class SubscriptionGroup(TagParseMixin, db.Model):
    """
    A group of subscriptions ("friendships") by category, rather like
    "Circles" in G+.

    Fields:
        id - an integer identifier uniquely identifying this group in the node
        user - the User this group belongs to
        user_id - the database primary key of the above
        name - the category name. Must be unique for the user
        subscriptions - a list of Subscriptions that are part of this group
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

    @classmethod
    def get_by_name(cls, name, user, create=True):
        """
        Returns the group named <group> owned by User <user>. If the group
        does not exist and <create> is False, None will be returned. If
        <create> is True, a new SubscriptionGroup will be created and returned.
        The caller may need to commit the new group.
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
