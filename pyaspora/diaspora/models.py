from sqlalchemy import Column, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import backref, relationship

from pyaspora import db


class DiasporaContact(db.Model):
    __tablename__ = 'diaspora_contacts'
    contact_id = Column(Integer, ForeignKey('contacts.id'), primary_key=True)
    guid = Column(String, nullable=False)
    username = Column(String, nullable=False)
    server = Column(String, nullable=False)

    contact = relationship('Contact', single_parent=True,
                           backref=backref('diasp', uselist=False))


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
