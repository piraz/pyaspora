from sqlalchemy import Column, Integer, LargeBinary, String

from pyaspora.database import Base

class MimePart(Base):
    """
    A piece of content (eg. text, HTML, image, video) that forms part of a Post.

    Fields:
        id - an integer identifier uniquely identifying this group in the node
        type - the MIME type (eg. "text/plain") of the body
        body - the raw content blob
        text_preview - plain text that can be displayed in lieu of content if the body cannot be displayed
    """
    __tablename__ = 'mime_parts'
    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)
    body = Column(LargeBinary, nullable=False)
    text_preview = Column(String, nullable=False)