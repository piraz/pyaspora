"""
Actions/display relating to Contacts. These may be locally-mastered (who
can also do User actions), but they may be Contacts on other nodes using
cached information.
"""

from __future__ import absolute_import

from datetime import timedelta
from flask import Blueprint, current_app, request, url_for, \
    abort as flask_abort
from hashlib import md5
from lxml import etree
from re import match as re_match
from traceback import format_exc
from sqlalchemy.orm import contains_eager
from sqlalchemy.sql import desc, or_

from pyaspora.contact.models import Contact
from pyaspora.database import db
from pyaspora.tag.views import json_tag
from pyaspora.utils import get_server_name
from pyaspora.utils.rendering import abort, add_logged_in_user_to_data, \
    raw_response, redirect, render_response, send_xml
from pyaspora.user.session import logged_in_user, require_logged_in_user

blueprint = Blueprint('contacts', __name__, template_folder='templates')


class FakePart:
    pass


@blueprint.route('/<int:contact_id>/avatar', methods=['GET'])
def avatar(contact_id):
    """
    Display the photo (or other media item) that represents a Contact.
    If the user is logged in they can view the avatar for any contact, but
    if not logged in then only locally-mastered contacts have their avatar
    displayed.
    """
    contact = Contact.get(contact_id)
    if not contact:
        abort(404, 'No such contact', force_status=True)
    if not contact.user and not logged_in_user():
        abort(404, 'No such contact', force_status=True)

    part = contact.avatar
    if not part:
        abort(404, 'Contact has no avatar', force_status=True)

    return raw_response(part.body, part.type, expiry_delta=timedelta(hours=12))


def _profile_base(contact_id, public=False):
    """
    Standard data for profile-alike pages, including the profile page and feed
    pages.
    """
    from pyaspora.post.models import Post, Share
    from pyaspora.post.views import json_posts

    contact = Contact.get(contact_id)
    if not contact:
        abort(404, 'No such contact', force_status=True)

    viewing_as = None if public else logged_in_user()

    data = json_contact(contact, viewing_as)
    limit = int(request.args.get('limit', 99))

    if viewing_as and request.args.get('refresh', False) and contact.diasp:
        try:
            contact.diasp.import_public_posts()
            db.session.commit()
        except:
            current_app.logger.debug(format_exc())

    # If not local, we don't have a proper feed
    if viewing_as or contact.user:
        # user put it on their public wall
        feed_query = Post.Queries.public_wall_for_contact(contact)
        if viewing_as:
            # Also include things this user has shared with us
            shared_query = Post.Queries.author_shared_with(
                contact, viewing_as)
            feed_query = or_(feed_query, shared_query)

        feed = db.session.query(Share). \
            join(Post). \
            filter(feed_query). \
            order_by(desc(Post.thread_modified_at)). \
            group_by(Post.id). \
            options(contains_eager(Share.post)). \
            limit(limit)

        data['feed'] = json_posts([(s.post, s) for s in feed], viewing_as)

    add_logged_in_user_to_data(data, viewing_as)
    return data, contact


@blueprint.route('/<int:contact_id>/profile', methods=['GET'])
def profile(contact_id):
    """
    Display the profile (possibly with feed) for the contact.
    """
    data, contact = _profile_base(
        contact_id,
        request.args.get('public', False)
    )
    if not contact.user and not logged_in_user():
        abort(404, 'No such contact', force_status=True)
    if contact.user and not contact.user.activated:
        abort(404, 'No such contact', force_status=True)
    return render_response('contacts_profile.tpl', data)


@blueprint.route('/<int:contact_id>/feed', methods=['GET'])
def feed(contact_id):
    """
    An Atom feed of public events for the contact. Only available for contacts
    who are local to this server.
    """
    data, contact = _profile_base(contact_id, public=True)
    if not(contact.user and contact.user.activated):
        flask_abort(404, 'No such user')

    # Fake "guid" for the user, derived from the ID
    guid = '{0}-{1}'.format(get_server_name(), contact.user.id)

    ns = 'http://www.w3.org/2005/Atom'
    doc = etree.Element("{%s}feed" % ns, nsmap={None: ns})
    etree.SubElement(doc, "title").text = u'Pyaspora feed for {0}'.format(
        data['name']
    )
    etree.SubElement(doc, "link").text = data['link']
    etree.SubElement(doc, "updated").text = data['feed'][0]['created_at'] \
        if data['feed'] else contact.user.activated.isoformat()
    etree.SubElement(doc, "id").text = guid
    etree.SubElement(doc, "generator").text = 'Pyaspora'

    author = etree.SubElement(doc, 'author')
    etree.SubElement(author, "name").text = data['name']
    etree.SubElement(author, "uri").text = data['link']

    for post in data['feed']:
        entry = etree.SubElement(doc, 'entry')
        etree.SubElement(entry, "id").text = \
            "{0}-{1}".format(guid, post['id'])
        etree.SubElement(entry, "title").text = \
            post['parts'][0]['body']['text']
        etree.SubElement(entry, "updated").text = post['created_at']
        etree.SubElement(entry, "content").text = \
            "\n\n".join(p['body']['text'] for p in post['parts'])

    return send_xml(doc)


def json_contact(contact, viewing_as=None):
    """
    A suitable representation of the contact that can be turned into JSON.
    If "viewing_as" (a local contact) is supplied, the data visible to that
    contact will be returned; otherwise only public data is visible.
    """
    from pyaspora.post.views import json_part
    resp = {
        'id': contact.id,
        'link': url_for(
            'contacts.profile',
            contact_id=contact.id,
            _external=True
        ),
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

    if contact.diasp:
        resp['username'] = contact.diasp.username

    # No point in showing subs for remote users as they're incomplete
    if contact.user:
        resp['subscriptions'] = url_for(
            'contacts.subscriptions',
            contact_id=contact.id,
            _external=True
        )

    if contact.avatar:
        resp['avatar'] = url_for(
            'contacts.avatar',
            contact_id=contact.id,
            _external=True
        )
    elif contact.user and \
            current_app.config.get('FEATURES', {}).get('gravatar', False):
        resp['avatar'] = 'http://www.gravatar.com/avatar/{}?d=mm'.format(
            md5(contact.user.email.strip().lower()).hexdigest()
        )

    if contact.bio:
        # Need something that feels like a PostPart for the rendering engine.
        fake_part = FakePart()
        fake_part.inline = True
        fake_part.mime_part = contact.bio
        resp['bio'] = json_part(fake_part)

    if viewing_as:
        if viewing_as.id == contact.id:  # Viewing own profile
            resp['actions'].update({
                'edit': url_for('users.info', _external=True)
            })
        elif viewing_as.contact.subscribed_to(contact):  # Friend
            resp['actions'].update({
                'remove': url_for(
                    'roster.unsubscribe',
                    contact_id=contact.id,
                    _external=True
                ),
                'post': url_for(
                    'posts.create',
                    target_type='contact',
                    target_id=contact.id,
                    _external=True
                ),
                'edit_groups': url_for(
                    'roster.edit_contact_groups_form',
                    contact_id=contact.id,
                    _external=True
                )
            })
        else:  # Potential friend? :-)
            resp['actions'].update({
                'add': url_for(
                    'roster.subscribe',
                    contact_id=contact.id,
                    _external=True
                )
            })

    return resp


@blueprint.route('/<int:contact_id>/subscriptions', methods=['GET'])
@require_logged_in_user
def subscriptions(contact_id, _user):
    """
    Display the friend list for the contact (who must be local to this server,
    because this server doesn't hold the full friend list for remote users).
    """
    contact = Contact.get(contact_id)
    if not(contact.user and contact.user.activated):
        abort(404, 'No such contact', force_status=True)

    # Looking at our own list? You'll be wanting the edit view.
    if contact.id == _user.contact.id:
        return redirect(url_for('roster.view', _external=True))

    data = json_contact(contact, _user)
    data['subscriptions'] = [json_contact(c, _user)
                             for c in contact.friends()]

    add_logged_in_user_to_data(data, _user)

    return render_response('contacts_friend_list.tpl', data)


@blueprint.route('/search', methods=['GET'])
@require_logged_in_user
def search(_user):
    from pyaspora.diaspora.models import DiasporaContact
    term = request.args.get('searchterm', None) or \
        abort(400, 'No search term provided')
    if re_match('[A-Za-z0-9._]+@[A-Za-z0-9.]+$', term):
        try:
            DiasporaContact.get_by_username(term)
        except:
            current_app.logger.debug(format_exc())

    matches = db.session.query(Contact).outerjoin(DiasporaContact).filter(or_(
        DiasporaContact.username.contains(term),
        Contact.realname.contains(term)
    )).order_by(Contact.realname).limit(99)

    data = {
        'contacts': [json_contact(c, _user) for c in matches]
    }

    add_logged_in_user_to_data(data, _user)

    return render_response('contacts_search_results.tpl', data)
