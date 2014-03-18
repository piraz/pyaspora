"""
Actions concerning a local User, who is mastered on this node.
"""
from __future__ import absolute_import

from Crypto.Hash import SHA256
from flask import Blueprint, current_app, request, session, url_for
from json import dumps as json_dumps

from pyaspora.contact.views import json_contact
from pyaspora.content.models import MimePart
from pyaspora.content.rendering import renderer_exists
from pyaspora.database import db
from pyaspora.tag.models import Tag
from pyaspora.user import models
from pyaspora.user.session import log_in_user, logged_in_user, \
    require_logged_in_user
from pyaspora.utils.email import send_template
from pyaspora.utils.validation import check_attachment_is_safe, post_param
from pyaspora.utils.rendering import abort, add_logged_in_user_to_data, \
    redirect, render_response

blueprint = Blueprint('users', __name__, template_folder='templates')


def _hash_for_pk(user):
    return SHA256.new(user.private_key.encode('ascii')).hexdigest()


@blueprint.route('/login', methods=['GET'])
def login():
    """
    Display the user login form.
    """
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
    """
    Log the user in, checking their credentials and configuring the session,
    and redirect them to the home page.
    """
    password = post_param('password', template='users_login_form.tpl')
    email = post_param('email', template='users_login_form.tpl')
    user = log_in_user(email, password)
    if not user:
        abort(403, 'Login failed')
    return redirect(url_for('index', _external=True))


@blueprint.route('/create', methods=['GET'])
def create_form():
    """
    Display the form to create a new user account.
    """
    if not current_app.config.get('ALLOW_CREATION', False):
        abort(403, 'Disabled by site administrator')
    return render_response('users_create_form.tpl')


@blueprint.route('/create', methods=['POST'])
def create():
    """
    Create a new User (sign-up).
    """
    if not current_app.config.get('ALLOW_CREATION', False):
        abort(403, 'Disabled by site administrator')

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

    send_template(my_user.email, 'user_activate_email.tpl', {
        'link': url_for(
            '.activate',
            user_id=my_user.id,
            key_hash=_hash_for_pk(my_user),
            _external=True
        )
    })

    data = {}
    add_logged_in_user_to_data(data, None)

    return render_response('users_created.tpl', data)


@blueprint.route('/logout', methods=['GET'])
def logout():
    """
    End a user session.
    """
    session['key'] = None
    session['user_id'] = None

    data = {}
    add_logged_in_user_to_data(data, None)

    return render_response('users_logged_out.tpl', data)


@blueprint.route('/activate/<int:user_id>/<string:key_hash>', methods=['GET'])
def activate(user_id, key_hash):
    """
    Activate a user. This is intended to be a clickable link from the sign-up
    email that confirms the email address is valid.
    """
    matched_user = models.User.get(user_id)

    if not matched_user:
        abort(404, 'Not found')

    if matched_user.activated:
        abort(404, 'Not found')

    if key_hash != _hash_for_pk(matched_user):
        abort(404, 'Not found')

    matched_user.activate()
    db.session.commit()
    return render_response('users_activation_success.tpl')


@blueprint.route('/info', methods=['GET'])
@require_logged_in_user
def info(_user):
    """
    Form to view or edit information on the currently logged-in user.
    """
    data = json_user(_user)
    add_logged_in_user_to_data(data, _user)
    data.update({
        'notification_frequency_hours': _user.notification_hours,
        'email': _user.email
    })
    return render_response('users_edit.tpl', data)


def json_user(user):
    """
    JSON-serialisable view of a User.
    """
    data = {
        'id': user.id,
        'email': user.email,
    }
    data.update(json_contact(user.contact))
    return data


@blueprint.route('/info', methods=['POST'])
@require_logged_in_user
def edit(_user):
    """
    Apply the changes from the user edit form. This updates such varied things
    as the profile photo and bio, the email address, name, password and
    interests.
    """
    from pyaspora.post.models import Post

    p = Post(author=_user.contact)
    changed = []
    order = 0

    notif_freq = post_param(
        'notification_frequency_hours',
        template='users_edit.tpl',
        optional=True
    )
    _user.notification_hours = int(notif_freq) if notif_freq else None

    email = post_param('email', optional=True)
    if email and email != _user.email:
        _user.email = email

    old_pw = post_param('current_password', optional=True)
    new_pw1 = post_param('new_password', optional=True)
    new_pw2 = post_param('new_password2', optional=True)
    if old_pw and new_pw1 and new_pw2:
        if new_pw1 != new_pw2:
            abort(400, 'New passwords do not match')
        try:
            _user.change_password(old_pw, new_pw1)
        except ValueError:
            abort(400, 'Old password is incorrect')
    db.session.add(_user)

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
            body=json_dumps({
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
