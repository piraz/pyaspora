"""
Actions/display relating to Contacts. These may be locally-mastered (who
can also do User actions), but they may be Contacts on other nodes using
cached information.
"""

from __future__ import absolute_import

from flask import Blueprint, make_response, request, url_for, \
    abort as flask_abort
from lxml import etree
from sqlalchemy.sql import desc, or_

from pyaspora.contact import models
from pyaspora.database import db
from pyaspora.tag.views import json_tag
from pyaspora.utils.rendering import abort, add_logged_in_user_to_data, \
    redirect, render_response, send_xml
from pyaspora.user.session import logged_in_user, require_logged_in_user

blueprint = Blueprint('contacts', __name__, template_folder='templates')


@blueprint.route('/<int:contact_id>/avatar', methods=['GET'])
def avatar(contact_id):
    """
    Display the photo (or other media) that represents a Contact.
    """
    contact = models.Contact.get(contact_id)
    if not contact:
        abort(404, 'No such contact', force_status=True)
    if not contact.user and not logged_in_user():
        abort(404, 'No such contact', force_status=True)

    part = contact.avatar
    if not part:
        abort(404, 'Contact has no avatar', force_status=True)

    response = make_response(part.body)
    response.headers['Content-Type'] = part.type
    return response


def _profile_base(contact_id, public=False):
    """
    Display the profile (possibly with feed) for the contact.
    """
    from pyaspora.post.models import Post, Share
    from pyaspora.post.views import json_posts

    contact = models.Contact.get(contact_id)
    if not contact:
        abort(404, 'No such contact', force_status=True)

    viewing_as = None if public else logged_in_user()

    data = json_contact(contact, viewing_as)
    limit = int(request.args.get('limit', 99))

    # If not local, we don't have a proper feed
    if contact.user:
        # user put it on their public wall
        feed_query = Post.Queries.public_wall_for_contact(contact)
        if viewing_as:
            # Also include things this user has shared with us
            shared_query = Post.Queries.author_shared_with(
                contact, viewing_as)
            feed_query = or_(feed_query, shared_query)
        feed = db.session.query(Post).join(Share).filter(feed_query). \
            order_by(desc(Post.thread_modified_at)). \
            group_by(Post.id).limit(limit)

        data['feed'] = json_posts([(p, None) for p in feed], viewing_as)

    add_logged_in_user_to_data(data, viewing_as)
    return data, contact


@blueprint.route('/<int:contact_id>/profile', methods=['GET'])
def profile(contact_id):
    data, contact = _profile_base(
        contact_id,
        request.args.get('public', False)
    )
    if not contact.user and not logged_in_user():
        abort(404, 'No such contact', force_status=True)
    return render_response('contacts_profile.tpl', data)


@blueprint.route('/<int:contact_id>/feed', methods=['GET'])
def feed(contact_id):
    data, contact = _profile_base(contact_id, public=True)
    if not contact.user:
        flask_abort(404, 'No such user')

    ns = 'http://www.w3.org/2005/Atom'
    doc = etree.Element("{%s}feed" % ns, nsmap={None: ns})
    etree.SubElement(doc, "title").text = \
        'Diaspora feed for {0}'.format(data['name'])
    etree.SubElement(doc, "link").text = data['link']
    etree.SubElement(doc, "updated").text = \
        data['feed'][0]['created_at'] if data['feed'] \
        else contact.user.activated.isoformat()
    etree.SubElement(doc, "id").text = contact.guid
    etree.SubElement(doc, "generator").text = 'Pyaspora'

    author = etree.SubElement(doc, 'author')
    etree.SubElement(author, "name").text = data['name']
    etree.SubElement(author, "uri").text = data['link']

    for post in data['feed']:
        entry = etree.SubElement(doc, 'entry')
        etree.SubElement(entry, "id").text = \
            "{0}-{1}".format(contact.guid, post['id'])
        etree.SubElement(entry, "title").text = \
            post['parts'][0]['body']['text']
        etree.SubElement(entry, "updated").text = post['created_at']
        etree.SubElement(entry, "content").text = \
            "\n\n".join([p['body']['text'] for p in post['parts']])

    return send_xml(doc)


def json_contact(contact, viewing_as=None):
    """
    A suitable representation of the contact that can be turned into JSON
    without too much problem.
    """
    resp = {
        'id': contact.id,
        'link': url_for('contacts.profile',
                        contact_id=contact.id, _external=True),
        'subscriptions': url_for('contacts.subscriptions',
                                 contact_id=contact.id, _external=True),
        'name': contact.realname,
        'bio': '',
        'avatar': None,
        'actions': {
            'add': None,
            'remove': None,
            'post': None,
            'edit': None,
            'edit_groups': None
        },
        'feed': None,
        'tags': [json_tag(t) for t in contact.interests]
    }
    if contact.avatar:
        resp['avatar'] = url_for('contacts.avatar',
                                 contact_id=contact.id, _external=True)

    if contact.bio:
        resp['bio'] = contact.bio.body.decode('utf-8')

    if viewing_as:
        if viewing_as.id == contact.id:
            resp['actions']['edit'] = url_for('users.info', _external=True)
        if viewing_as.contact.subscribed_to(contact):
            resp['actions']['remove'] = url_for('roster.unsubscribe',
                                                contact_id=contact.id,
                                                _external=True)
            resp['actions']['post'] = url_for('posts.create',
                                              target_type='contact',
                                              target_id=contact.id,
                                              _external=True)
            resp['actions']['edit_groups'] = url_for(
                'roster.edit_contact_groups_form',
                contact_id=contact.id,
                _external=True
            )
        else:
            if viewing_as.id != contact.id:
                resp['actions']['add'] = url_for('roster.subscribe',
                                                 contact_id=contact.id,
                                                 _external=True)

    return resp


@blueprint.route('/<int:contact_id>/subscriptions', methods=['GET'])
@require_logged_in_user
def subscriptions(contact_id, _user):
    """
    Display the friend list for the contact (who must be local to this
    server.
    """
    contact = models.Contact.get(contact_id)
    if not contact or not contact.user:
        abort(404, 'No such contact', force_status=True)

    if contact.id == _user.contact.id:
        return redirect(url_for('roster.view', _external=True))

    data = json_contact(contact, _user)
    data['subscriptions'] = [json_contact(c, _user)
                             for c in contact.friends()]

    add_logged_in_user_to_data(data, _user)

    return render_response('contacts_friend_list.tpl', data)
