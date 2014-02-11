import re
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import joinedload, relationship
from sqlalchemy.sql import and_, not_

from pyaspora.database import db


class Interest(db.Model):
    '''
    Link between a Contact and a Tag, indicating that the Contact has an
    interest in the Tag's topic.

    Fields:
        contact_id - integer ID for the Contact
        tag_id - integer ID for the Tag
    '''

    __tablename__ = 'interests'
    contact_id = Column(Integer, ForeignKey('contacts.id'), primary_key=True)
    tag_id = Column(Integer, ForeignKey('tags.id'),
                    primary_key=True, index=True)


class PostTag(db.Model):
    '''
    Link between a Post and a Tag, indicating that the Post has the Tag as a
    topic.

    Fields:
        post_id - integer ID for the Post
        tag_id - integer ID for the Tag
    '''

    __tablename__ = 'post_tags'
    post_id = Column(Integer, ForeignKey('posts.id'), primary_key=True)
    tag_id = Column(Integer, ForeignKey('tags.id'),
                    primary_key=True, index=True)

    @classmethod
    def get_tags_for_posts(cls, post_ids):
        return db.session.query(cls). \
            options(joinedload(cls.tag)). \
            filter(cls.post_id.in_(post_ids))


class Tag(db.Model):
    '''
    A topic that can be attached to a Post, or to a Contact (as an
    'interest'), for categorising and filtering content.

    Fields:
        id - integer ID for the tag
        name - human-readable tag description
        contacts - Contacts interested in this tag
        posts - Posts tagged with this tag
    '''

    __tablename__ = 'tags'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

    contacts = relationship('Contact',
                            secondary='interests', backref='interests')
    posts = relationship('Post', secondary='post_tags', backref='tags')
    post_tags = relationship('PostTag', backref='tag')

    class Queries:
        @classmethod
        def public_posts_for_tags(cls, tag_ids):
            from pyaspora.post.models import Share
            return and_(
                Tag.id.in_(tag_ids),
                not_(Share.hidden),
                Share.public,
            )

    @classmethod
    def name_is_valid(cls, name):
        if not name:
            return False

        if len(name) > 100:
            return False

        if re.search(r'[^a-z0-9_]', name):
            return False

        if '__' in name:
            return False

        if name.startswith('_'):
            return False

        if name.endswith('_'):
            return False

        return True

    @classmethod
    def get_by_name(cls, name, create=True):
        if not cls.name_is_valid(name):
            return

        tag = db.session.query(cls).filter(cls.name == name).first()
        if create and not tag and cls.name_is_valid(name):
            tag = cls(name=name)
            db.session.add(tag)

        return tag

    @classmethod
    def parse_line(cls, line, create=True):
        tags = []
        for possible_tag in re.split('[,\s]+', line):
            tag = cls.get_by_name(possible_tag.lower(), create)
            if tag:
                tags.append(tag)
        return tags
