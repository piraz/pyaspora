"""
Actions/display relating to Contacts. These may be locally-mastered (who
can also do User actions), but they may be Contacts on other nodes using
cached information.
"""

from flask import Blueprint, make_response, request, url_for
from sqlalchemy.sql import and_, desc, not_, or_

from pyaspora.contact import models
from pyaspora.database import db
from pyaspora.utils.rendering import abort, redirect, render_response
from pyaspora.user.session import logged_in_user

blueprint = Blueprint('contacts', __name__, template_folder='templates')


@blueprint.route('/<int:contact_id>/avatar', methods=['GET'])
def avatar(contact_id):
    """
    Display the photo (or other media) that represents a Contact.
    """
    contact = models.Contact.get(contact_id)
    if not contact or not contact.user:
        abort(404, 'No such contact', force_status=True)

    part = contact.avatar
    if not part:
        abort(404, 'Contact has no avatar', force_status=True)

    response = make_response(part.body)
    response.headers['Content-Type'] = part.type
    return response


@blueprint.route('/<int:contact_id>/profile', methods=['GET'])
def profile(contact_id):
    """
    Display the profile (possibly with feed) for the contact.
    """
    from pyaspora.post.models import Post, Share
    from pyaspora.post.views import json_post
    contact = models.Contact.get(contact_id)
    if not contact:
        abort(404, 'No such contact', force_status=True)

    viewing_as = logged_in_user() if not request.args.get('public', False) \
        else None

    data = json_contact(contact, viewing_as)
    limit = int(request.args.get('limit', 99))

    # If not local, we don't have a proper feed
    if contact.user:
        # user put it on their public wall
        feed_query = and_(Share.contact_id == contact.id,
                          Share.public,
                          not_(Share.hidden))
        if viewing_as:
            # Also include things this user has shared with us
            shared_query = and_(Post.author_id == contact.id,
                                Share.contact_id == viewing_as.contact.id,
                                not_(Share.hidden))
            feed_query = or_(feed_query, shared_query)
        feed = db.session.query(Share).join(Post).filter(feed_query) \
            .order_by(desc(Post.created_at))[0:limit]

        data['feed'] = [json_post(s.post, viewing_as) for s in feed]

    return render_response('profile.tpl', data)


def json_contact(contact, viewing_as=None):
    """
    A suitable representation of the contact that can be turned into JSON
    without too much problem.
    """
    resp = {
        'id': contact.id,
        'link': url_for('contacts.profile',
                        contact_id=contact.id, _external=True),
        'friends': url_for('contacts.friends',
                           contact_id=contact.id, _external=True),
        'name': contact.realname,
        'bio': '',
        'avatar': None,
        'actions': {
            'add': None,
            'remove': None,
            'post': None,
            'edit': None
        },
        'feed': None
    }
    if contact.avatar:
        resp['avatar'] = url_for('contacts.avatar',
                                 contact_id=contact.id, _external=True)

    if contact.bio:
        resp['bio'] = contact.bio.text_preview

    if viewing_as:
        if viewing_as.id == contact.id:
            resp['actions']['edit'] = url_for('users.info', _external=True)
        if viewing_as.subscribed_to(contact):
            resp['actions']['remove'] = url_for('roster.unsubscribe',
                                                contact_id=contact.id,
                                                _external=True)
        else:
            resp['actions']['post'] = url_for('posts.create',
                                              target='contact',
                                              target_id=contact.id)
            if viewing_as.id != contact.id:
                resp['actions']['add'] = url_for('roster.subscribe',
                                                 contact_id=contact.id,
                                                 _external=True)

    return resp


@blueprint.route('/<int:contact_id>/friends', methods=['GET'])
def friends(contact_id):
    """
    Display the friend list for the contact (who must be local to this
    server.
    """
    user = logged_in_user()
    if not user:
        abort(401, 'Not logged in')

    contact = models.Contact.get(contact_id)
    if not contact or not contact.user:
        abort(404, 'No such contact', force_status=True)

    if contact.id == user.contact.id:
        return redirect(url_for('roster.view', _external=True))

    data = json_contact(contact, user)
    data['friends'] = [json_contact(c, user) for c in contact.user.friends()]

    return render_response('friend_list.tpl', data)
