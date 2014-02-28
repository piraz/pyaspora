"""
Actions concerning a local User, who is mastered on this node.
"""

import json
from flask import Blueprint, request, session, url_for

from pyaspora.contact.views import json_contact
from pyaspora.content.models import MimePart
from pyaspora.content.rendering import renderer_exists
from pyaspora.database import db
from pyaspora.tag.models import Tag
from pyaspora.user import models
from pyaspora.user.session import log_in_user, logged_in_user, \
    require_logged_in_user
from pyaspora.utils.validation import check_attachment_is_safe, post_param
from pyaspora.utils.rendering import abort, add_logged_in_user_to_data, \
    redirect, render_response

blueprint = Blueprint('users', __name__, template_folder='templates')


@blueprint.route('/login', methods=['GET'])
def login():
    user = logged_in_user()
    if user:
        data = {}
        add_logged_in_user_to_data(data, user)
        abort(400, 'Already logged in', data)

    data = {}
    add_logged_in_user_to_data(data, None)

    return render_response('users_login_form.tpl', data)


@blueprint.route('/login', methods=['POST'])
def process_login():
    password = post_param('password', template='users_login_form.tpl')
    email = post_param('email', template='users_login_form.tpl')
    user = log_in_user(email, password)
    if not user:
        abort(403, 'Login failed')
    return redirect(url_for('index', _external=True))


@blueprint.route('/create', methods=['GET'])
def create_form():
    return render_response('users_create_form.tpl')


@blueprint.route('/create', methods=['POST'])
def create():
    """
    Create a new User (sign-up).
    """
    user = logged_in_user()
    if user:
        data = {}
        add_logged_in_user_to_data(data, user)
        abort(400, 'Already logged in', data)

    name = post_param('name', template='users_create_form.tpl')
    password = post_param('password', template='users_create_form.tpl')
    email = post_param('email', template='users_create_form.tpl')

    my_user = models.User()
    my_user.email = email
    my_user.contact.realname = name
    my_user.generate_keypair(password)
    db.session.commit()

    data = {}
    add_logged_in_user_to_data(data, None)

    return render_response('users_created.tpl', data)


@blueprint.route('/logout', methods=['GET'])
def logout():
    session['key'] = None
    session['user_id'] = None

    data = {}
    add_logged_in_user_to_data(data, None)

    return render_response('users_logged_out.tpl', data)


@blueprint.route('/activate/<int:user_id>/<string:key_hash>', methods=['GET'])
def activate(user_id, key_hash):
    """
    Activate a user. This is intended to be a clickable link from the
    sign-up email that confirms the email address is valid.
    """
    matched_user = models.User.get(user_id)
    return  # FIXME

    if not matched_user:
        abort(404, 'Not found')

    matched_user.activate()
    db.session.commit()
    return render_response('users_activation_success.tpl')


@blueprint.route('/info', methods=['GET'])
@require_logged_in_user
def info(_user):
    data = json_user(_user)
    add_logged_in_user_to_data(data, _user)
    return render_response('users_edit.tpl', data)


def json_user(user):
    data = {
        'id': user.id,
        'email': user.email,
    }
    data.update(json_contact(user.contact))
    return data


@blueprint.route('/info', methods=['POST'])
@require_logged_in_user
def edit(_user):
    from pyaspora.post.models import Post

    p = Post(author=_user.contact)
    changed = []
    order = 0

    attachment = request.files.get('avatar', None)
    if attachment and attachment.filename:
        changed.append('avatar')
        order += 1
        check_attachment_is_safe(attachment)

        if not renderer_exists(attachment.mimetype) or \
                not attachment.mimetype.startswith('image/'):
            abort(400, 'Avatar format unsupported')

        attachment_part = MimePart(
            type=attachment.mimetype,
            body=attachment.stream.read(),
            text_preview=attachment.filename
        )

        p.add_part(attachment_part, order=order, inline=True)
        _user.contact.avatar = attachment_part

    name = post_param('name', template='users_edit.tpl', optional=True)
    if name and name != _user.contact.realname:
        _user.contact.realname = name
        changed.append('name')

    bio = post_param('bio', template='users_edit.tpl', optional=True)
    if bio:
        bio = bio.encode('utf-8')
    else:
        bio = b''
    if bio and (not _user.contact.bio or _user.contact.bio.body != bio):
        changed.append('bio')
        order += 1
        bio_part = MimePart(body=bio, type='text/plain', text_preview=None)
        p.add_part(
            order=order,
            inline=True,
            mime_part=bio_part
        )
        _user.contact.bio = bio_part

    tags = post_param('tags', optional=True)
    if tags is not None:
        tag_objects = Tag.parse_line(tags, create=True)
        old_tags = set([t.id for t in _user.contact.interests])
        new_tags = set([t.id for t in tag_objects])
        if old_tags != new_tags:
            changed.append('tags')
            _user.contact.interests = tag_objects

    p.add_part(
        order=0,
        inline=True,
        mime_part=MimePart(
            body=json.dumps({
                'fields_changed': changed
            }).encode('utf-8'),
            type='application/x-pyaspora-profile-update',
            text_preview='updated their profile'
        )
    )

    if changed:
        db.session.add(p)
        db.session.add(_user.contact)
        p.share_with([_user.contact])
        p.thread_modified()
        db.session.commit()

    return redirect(url_for('contacts.profile', contact_id=_user.contact.id))
