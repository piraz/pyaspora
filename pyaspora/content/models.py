from sqlalchemy import Column, Integer, LargeBinary, String

from pyaspora.database import db


class MimePart(db.Model):
    """
    A piece of content (eg. text, HTML, image, video) that forms part of a
    Post.

    Fields:
        id - an integer identifier uniquely identifying this group in the node
        type - the MIME type (eg. "text/plain") of the body
        body - the raw content blob
        text_preview - plain text that can be displayed in lieu of content if
                       the body cannot be displayed
    """
    __tablename__ = 'mime_parts'
    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)
    body = Column(LargeBinary, nullable=False)
    text_preview = Column(String, nullable=False)

    @classmethod
    def get(cls, part_id):
        """
        Get a contact by primary key ID. None is returned if the Contact
        doesn't exist.
        """
        return db.session.query(cls).get(part_id)
