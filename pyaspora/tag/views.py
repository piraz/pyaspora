from flask import Blueprint, url_for

from pyaspora.tag.models import Tag

blueprint = Blueprint('tags', __name__, template_folder='templates')

def json_tag(tag):
    return {
        'id': tag.id,
        'name': tag.name
    }
