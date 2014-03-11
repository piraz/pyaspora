from __future__ import absolute_import

from flask import Blueprint, request, url_for
from sqlalchemy.sql import desc, or_
from sqlalchemy.orm import contains_eager

from pyaspora.database import db
from pyaspora.post.models import Post, Share
from pyaspora.post.views import json_posts
from pyaspora.tag.models import PostTag, Tag
from pyaspora.user.session import require_logged_in_user
from pyaspora.utils.rendering import add_logged_in_user_to_data, \
    redirect, render_response

blueprint = Blueprint('feed', __name__, template_folder='templates')


@blueprint.route('/', methods=['GET'])
@require_logged_in_user
def view(_user):
    """
    Show the logged-in user their own feed.
    """
    from pyaspora.diaspora.models import MessageQueue
    if MessageQueue.has_pending_items(_user):
        return redirect(url_for('diaspora.run_queue', _external=True))

    limit = int(request.args.get('limit', 99))
    friend_ids = [f.id for f in _user.contact.friends()]
    clauses = [Post.Queries.shared_with_contact(_user.contact)]
    if friend_ids:
        clauses.append(
            Post.Queries.authored_by_contacts_and_public(friend_ids))
    tag_ids = [t.id for t in _user.contact.interests]
    if tag_ids:
        clauses.append(Tag.Queries.public_posts_for_tags(tag_ids))
    feed_query = or_(*clauses)
    feed = db.session.query(Share).join(Post). \
        outerjoin(PostTag).outerjoin(Tag). \
        filter(feed_query). \
        order_by(desc(Post.thread_modified_at)). \
        group_by(Post.id). \
        options(contains_eager(Share.post)). \
        limit(limit)

    data = {
        'feed': json_posts([(s.post, s) for s in feed], _user)
    }

    add_logged_in_user_to_data(data, _user)

    return render_response('feed.tpl', data)
