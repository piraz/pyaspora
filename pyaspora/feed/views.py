from __future__ import absolute_import

from flask import Blueprint, request, url_for
from sqlalchemy.sql import and_, desc, not_, or_
from sqlalchemy.orm import aliased, contains_eager, joinedload

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

    limit = int(request.args.get('limit', 10))
    friend_ids = [f.id for f in _user.contact.friends()]
    clauses = [Post.Queries.shared_with_contact(_user.contact)]
    if friend_ids:
        clauses.append(
            Post.Queries.authored_by_contacts_and_public(friend_ids))
    tag_ids = [t.id for t in _user.contact.interests]
    if tag_ids:
        clauses.append(Tag.Queries.public_posts_for_tags(tag_ids))
    feed_query = or_(*clauses)
    my_share = aliased(Share)
    feed = db.session.query(Share).join(Post). \
        outerjoin(  # Stuff user hasn't hidden
            my_share,
            and_(
                Post.id == my_share.post_id,
                my_share.contact == _user.contact
            )
        ). \
        outerjoin(PostTag).outerjoin(Tag). \
        filter(feed_query). \
        filter(or_(my_share.hidden == None, not_(my_share.hidden))). \
        filter(Post.parent == None). \
        order_by(desc(Post.thread_modified_at)). \
        group_by(Post.id). \
        options(contains_eager(Share.post)). \
        options(joinedload(Share.post, Post.diasp)). \
        limit(limit)

    data = {
        'feed': json_posts([(s.post, s) for s in feed], _user, True),
        'limit': limit,
    }
    if len(data['feed']) >= limit:
        data['next'] = url_for('feed.view', limit=limit + 10, _external=True)

    add_logged_in_user_to_data(data, _user)

    return render_response('feed.tpl', data)
