from __future__ import absolute_import

from datetime import timedelta
from flask import Blueprint

from pyaspora.content.models import MimePart
from pyaspora.user.session import logged_in_user
from pyaspora.utils.rendering import abort, raw_response

blueprint = Blueprint('content', __name__, template_folder='templates')


@blueprint.route('/<int:part_id>/raw', methods=['GET'])
def raw(part_id):
    """
    Return the part's body as a raw byte-stream for eg. serving images.
    """
    part = MimePart.get(part_id)
    logged_in = logged_in_user()
    if not part:
        abort(404, 'No such content item', force_status=True)

    # If anyone has shared this part with us (or the public), we get to view
    # it.
    for link in part.posts:
        if link.post.has_permission_to_view(logged_in):
            return raw_response(
                part.body,
                part.type,
                expiry_delta=timedelta(days=365)
            )

    abort(403, 'Forbidden')
