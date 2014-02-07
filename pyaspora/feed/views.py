from flask import Blueprint, request
from sqlalchemy.sql import desc, or_

from pyaspora.database import db
from pyaspora.post.models import Post, Share
from pyaspora.post.views import json_post
from pyaspora.tag.models import PostTag, Tag
from pyaspora.user.session import require_logged_in_user
from pyaspora.utils.rendering import add_logged_in_user_to_data, \
    render_response

blueprint = Blueprint('feed', __name__, template_folder='templates')


@blueprint.route('/', methods=['GET'])
@require_logged_in_user
def view(_user):
    """
    Show the logged-in user their own feed.
    """
    limit = int(request.args.get('limit', 99))
    friend_ids = [f.id for f in _user.friends()]
    clauses = [Post.Queries.shared_with_contact(_user.contact)]
    if friend_ids:
        clauses.append(Post.Queries.authored_by_contacts_and_public(friend_ids))
    tag_ids = [t.id for t in _user.contact.interests]
    if tag_ids:
        clauses.append(Tag.Queries.public_posts_for_tags(tag_ids))
    feed_query = or_(**clauses)
    feed = db.session.query(Share).join(Post) \
        .outerjoin(PostTag).outerjoin(Tag) \
        .filter(feed_query) \
        .order_by(desc(Post.created_at)).limit(limit)

    data = {
        'feed': [json_post(s.post, _user, s) for s in feed],
    }

    add_logged_in_user_to_data(data, _user)

    return render_response('feed.tpl', data)
