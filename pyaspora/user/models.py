from __future__ import absolute_import

from Crypto.PublicKey import RSA
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import backref, joinedload, relationship
from sqlalchemy.sql.expression import func

from pyaspora.contact.models import Contact
from pyaspora.database import db
from pyaspora.utils.email import send_template


class User(db.Model):
    """
    A local user who is based on this node, and who can log in, view their
    feed and manage their account. Users are associated with a Contact which
    is their external representation - thus, all Users must have a contact.

    Fields:
        id - an integer identifier uniquely identifying this group in the node
        email - the user's email address. Must be unique across the node.
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
    private_key = Column(String, nullable=False)
    contact_id = Column(Integer, ForeignKey('contacts.id'), nullable=False)
    activated = Column(DateTime(timezone=True), nullable=True, default=None)
    notification_hours = Column(Integer, nullable=True, default=None)
    last_notified = Column(DateTime(timezone=True), nullable=True,
                           default=None)

    contact = relationship(Contact, single_parent=True,
                           backref=backref('user', uselist=False))

    @classmethod
    def get(cls, user_id):
        """
        Get a user by primary key ID. Returns None if the user cannot be found.
        """
        return db.session.query(cls). \
            options(joinedload(cls.contact)). \
            get(user_id)

    @classmethod
    def get_by_email(cls, email):
        """
        Fetches a user by email address.
        """
        return db.session.query(cls).filter(cls.email == email).first()

    def __init__(self, contact=None):
        """
        Creates a new user, creating a new Contact for the user if none is
        supplied. The contact is then associated with the newly created User.
        """
        db.Model.__init__(self)
        if not contact:
            contact = Contact()
        self.contact = contact
        db.session.add(self)

    def notify_event(self):
        if not self.activated:
            return  # notifications disabled until activated

        if not self.notification_hours:
            return  # notifications disabled

        if last_notified and last_notified > \
                datetime.now() - timedelta(hours=self.notification_hours):
            return  # too soon

        send_template(self.email, 'user_event_email.tpl', {})

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

    def generate_keypair(self, passphrase):
        """
        Generate a 2048-bit RSA key. The key will be stored in the User
        object. The private key will be protected with password <passphrase>,
        which is usually the user password.
        """
        RSAkey = RSA.generate(2048)
        self.private_key = RSAkey.exportKey(
            format='PEM', pkcs=1, passphrase=passphrase).decode("ascii")
        self.contact.public_key = RSAkey.publickey().exportKey(
            format='PEM', pkcs=1).decode("ascii")
