import re
from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import and_

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
    tag_id = Column(Integer, ForeignKey('tags.id'), primary_key=True)


class PostTag(db.Model):
    '''
    Link between a Post and a Tag, indicating that the Post has the Tag as a
    topic.

    Fields:
        post_id - integer ID for the Post
        tag_id - integer ID for the Tag
    '''

    __tablename__ = 'post_tags'
    contact_id = Column(Integer, ForeignKey('posts.id'), primary_key=True)
    tag_id = Column(Integer, ForeignKey('tags.id'), primary_key=True)


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

    contacts = relationship('Contact', secondary='interests', backref='interests')
    posts = relationship('Post', secondary='post_tags', backref='tags')

    @classmethod
    def name_is_valid(cls, name):
        if not name:
            return False

        if len(name) > 100:
            return False

        if re.match(r'[^a-z0-9_]', name):
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
            db.session.commit()

        return tag

    @classmethod
    def parse_line(cls, line, create=True):
        tags = []
        for possible_tag in line.split():
            tag = cls.get_by_name(possible_tag.lower(), create)
            if tag:
                tags.append(tag)
        return tags
