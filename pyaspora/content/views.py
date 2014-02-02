from flask import Blueprint, make_response

from pyaspora.content.models import MimePart
from pyaspora.user.session import logged_in_user
from pyaspora.utils.rendering import abort

blueprint = Blueprint('content', __name__, template_folder='templates')


@blueprint.route('/<int:part_id>/raw', methods=['GET'])
def raw(part_id):
    part = MimePart.get(part_id)
    logged_in = logged_in_user()
    if not part:
        abort(404, 'No such content item', force_status=True)

    # If anyone has shared this part with us (or the public), we get to view
    # it.
    for link in part.posts:
        if link.post.has_permission_to_view(logged_in):
            ret = make_response(part.body)
            ret.headers['Content-Type'] = part.type
            return ret

    abort(403, 'Forbidden')
