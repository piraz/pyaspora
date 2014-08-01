from __future__ import absolute_import

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import backref, contains_eager, relationship
from sqlalchemy.sql import and_, not_
from sqlalchemy.sql.expression import func

from pyaspora.content.models import MimePart
from pyaspora.contact.models import Contact
from pyaspora.database import db


class Share(db.Model):
    """
    Represents a Post being displayed to a Contact, for example in their feed
    or on their wall.

    Fields:
        contact - the Contact the Post is being displayed to
        contact_id - the database primary key of the above
        post - the Post that is being shared with <contact>
        post_id - the database primary key of the above
        public - whether the post is shown on the user's public wall
        hidden - whether the author has hidden the post from their feed
        shared_at - the DateTime the Post was shared with the Contact (that
                    is, the Share creation date)
    """
    __tablename__ = 'shares'
    contact_id = Column(Integer, ForeignKey('contacts.id'), primary_key=True)
    post_id = Column(Integer, ForeignKey('posts.id'),
                     primary_key=True, index=True)
    public = Column(Boolean, nullable=False)
    hidden = Column(Boolean, nullable=False, default=False)
    shared_at = Column(DateTime(timezone=True),
                       nullable=False, default=func.now())

    contact = relationship(Contact, backref="feed", order_by='Share.shared_at')

    @classmethod
    def get_for_posts(cls, post_ids):
        return db.session.query(cls).filter(cls.post_id.in_(post_ids))


class PostPart(db.Model):
    """
    A link between a Post and a MIMEPart, specifying the order of parts in a
    Post. This class exists because one MIMEPart may be part of several Posts,
    for example where a Post is re-shared (which creates a new Post but with
    the same content (plus an additional comment).

    Fields:
        post - the Post this PostPart belongs to
        post_id - the database primary key for the above
        mime_part - the MimePart this PostPart links to
        mime_part_id - the database primary key for the above
        order - an integer specifying the sort order for the Post's PostParts,
                sorted ascending numerically
        inline - a boolean hint as to whether the part should be displayed
                 inline or as an attachment
    """
    __tablename__ = 'post_parts'
    post_id = Column(Integer, ForeignKey('posts.id'), primary_key=True)
    mime_part_id = Column(Integer, ForeignKey('mime_parts.id'),
                          primary_key=True, index=True)
    order = Column(Integer, nullable=False, default=0)
    inline = Column(Boolean, nullable=False, default=True)

    mime_part = relationship(MimePart, backref='posts')

    @classmethod
    def get_parts_for_posts(cls, post_ids):
        """
        Fetch all the PostParts, with MimeParts pre-loaded, for the all the
        Posts with IDs <post_ids>.
        """
        if not post_ids:
            return []
        return db.session.query(cls). \
            join(MimePart). \
            filter(cls.post_id.in_(post_ids)). \
            options(contains_eager(cls.mime_part))


class Post(db.Model):
    """
    A post (a collection of parts (text, images, etc) that together form an
    entry on a wall/feed etc.

    Fields:
        id - an integer identifier uniquely identifying this group in the node
        author - the Contact that authored the post
        author_id - the database primary key for the above
        parent - if this Post is a comment on another Post, this links to the
                 parent Post. May be None.
        parent_id - the database primary key for the above
        thread_modified_at - last modification of the post or children, only
                             set on posts with no parent (top-level items)
        shares - Shares of this Post (occurrences in feeds/on walls)
        parts - PostParts that this Post consists of (the Post contents)
        children - Posts that have this post as the parent
    """
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey('contacts.id'),
                       nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey('posts.id'), nullable=True,
                       default=None, index=True)
    created_at = Column(DateTime(timezone=True),
                        nullable=False, default=func.now())
    thread_modified_at = Column(DateTime(timezone=True), nullable=True)

    author = relationship(Contact, backref='posts')
    parts = relationship(PostPart, backref='post', order_by=PostPart.order)
    children = relationship('Post',
                            backref=backref('parent', remote_side=[id]))
    shares = relationship(Share, backref='post')

    class Queries:
        @classmethod
        def public_wall_for_contact(cls, contact):
            return and_(
                Share.contact_id == contact.id,
                Share.public,
                not_(Share.hidden),
                Post.parent_id == None
            )

        @classmethod
        def author_shared_with(cls, author, target):
            return and_(
                Post.author_id == author.id,
                Share.contact_id == target.contact.id,
                not_(Share.hidden),
                Post.parent_id == None
            )

        @classmethod
        def shared_with_contact(cls, contact):
            return Share.contact_id == contact.id

        @classmethod
        def authored_by_contacts_and_public(cls, contact_ids):
            return and_(
                Share.contact_id.in_(contact_ids),
                not_(Share.hidden),
                Share.public
            )

        @classmethod
        def children_for_posts(cls, post_ids):
            return Post.parent_id.in_(post_ids)

    @classmethod
    def get(cls, postid):
        """
        Get a Post by primary key ID. Returns None if the Post doesn't exist.
        """
        return db.session.query(cls).get(postid)

    def has_permission_to_view(self, contact=None, share=False):
        """
        Whether the Contact <contact> is permitted to view this post.
        """
        if contact:
            # Check for shares to the contact
            if share is False:  # we don't use None as there may be no Share
                share = self.shared_with(contact)

            if share:
                # Hidden status trumps everything else
                return not share.hidden

            # Can always view my own stuff
            if contact.id == self.author_id:
                return True

        if share and share.public:
            return True

        return bool(self.is_public())

    def viewable_children(self, contact=None):
        """
        List of child posts that the Contact <contact> is permitted to view
        """
        return [child for child in self.children
                if child.has_permission_to_view(contact)]

    def add_part(self, mime_part, inline=False, order=1):
        """
        Adds MIMEPart <mimepart> to this Post, creating the linking PostPart
        (which is returned).
        """
        link = PostPart(post=self, mime_part=mime_part, inline=inline,
                        order=order)
        db.session.add(link)
        return link

    def is_public(self):
        """
        Returns true if anybody has made this Post public.
        """
        return db.session.query(Share).filter(and_(
            Share.public,
            Share.post == self
        )).first()

    def author_made_public(self):
        """
        Returns true if the original author made this Post public.
        """
        return db.session.query(Share).filter(and_(
            Share.contact == self.author,
            Share.public,
            Share.post == self
        )).first()

    def _send_to_remotes(self, contacts, reshare_of):
        """
        Arrange to send this post to contacts on the remote node.
        """
        from pyaspora.diaspora.models import DiasporaPost
        db.session.commit()  # write out shares
        contacts = [c for c in contacts if not c.user]
        if contacts:
            # Only public posts can be reshared by Diaspora
            if reshare_of and self.author_made_public() and \
                    reshare_of.author_made_public():
                DiasporaPost.get_for_post(self).reshare(contacts, reshare_of)
            else:
                DiasporaPost.get_for_post(self).send_to(contacts)

    def implicit_share(self, contacts, reshare_of=None):
        """
        Contacts can see the content because it is public, but it is not
        directly shared with them.
        """
        if self.author.user:
            # Only announce locally-generated content
            self._send_to_remotes(contacts, reshare_of)

    def share_with(self, contacts, show_on_wall=False, reshare_of=None):
        """
        Share this Post with all the contacts in list <contacts>. This method
        doesn't share the post if the Contact already has this Post shared
        with them.
        """
        new_shares = []
        for contact in contacts:
            if not self.shared_with(contact):
                new_shares.append(contact)
                db.session.add(Share(contact=contact, post=self,
                                     public=show_on_wall))
                if contact.user and contact.id != self.author_id:
                    contact.user.notify_event(commit=False)
        if self.author.user:
            # Only announce locally-generated content
            self._send_to_remotes(new_shares, reshare_of)

    def shared_with(self, contact):
        """
        Returns a boolean indicating whether this Post has already been shared
        with Contact <contact>.
        """
        return db.session.query(Share).filter(and_(
            Share.contact == contact,
            Share.post == self
        )).first()

    def hide(self, user):
        """
        Stop this post appearing in the feed of the user.
        """
        share = self.shared_with(user.contact)
        if share:
            share.hidden = True
            db.session.add(share)
            return

        # Can only make our own share for public posts
        assert(self.is_public())
        db.session.add(Share(
            contact=user.contact,
            post=self,
            public=True,
            hidden=True
        ))

    def root(self):
        """
        The top-level post that started this thread.
        """
        post = self
        while post.parent:
            post = post.parent
        return post

    def thread_modified(self, when=None):
        """
        Mark this thread as having been modified. This makes it "bubble up" in
        contact feeds. Requires the caller commit the session.
        """
        post = self.root()
        if when:
            if not(post.thread_modified_at) or post.thread_modified_at < when:
                post.thread_modified_at = when
        else:
            post.thread_modified_at = func.now()
        if post.id != self.id:
            db.session.add(post)
