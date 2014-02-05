from flask import Blueprint, request
from sqlalchemy.sql import and_, desc, not_

from pyaspora.database import db
from pyaspora.user.session import logged_in_user
from pyaspora.utils.rendering import abort, add_logged_in_user_to_data, \
    render_response

blueprint = Blueprint('feed', __name__, template_folder='templates')


@blueprint.route('/', methods=['GET'])
def view():
    """
    Show the logged-in user their own feed.
    """
    from pyaspora.post.models import Post, Share
    from pyaspora.post.views import json_post
    user = logged_in_user()
    if not user:
        abort(401, 'Not logged in')

    limit = int(request.args.get('limit', 99))
    feed_query = and_(Share.contact_id == user.contact.id,
                      not_(Share.hidden),
                      Post.parent_id == None)
    feed = db.session.query(Share).join(Post).filter(feed_query) \
        .order_by(desc(Post.created_at))[0:limit]

    data = {
        'feed': [json_post(s.post, user, s) for s in feed],
    }

    add_logged_in_user_to_data(data, user)

    return render_response('feed.tpl', data)
