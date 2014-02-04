"""
Actions concerning a local User, who is mastered on this node.
"""

import json
from flask import Blueprint, session, url_for

from pyaspora.contact.views import json_contact
from pyaspora.content.models import MimePart
from pyaspora.database import db
from pyaspora.user import models
from pyaspora.user.session import log_in_user, logged_in_user
from pyaspora.utils.validation import post_param
from pyaspora.utils.rendering import abort, redirect, render_response

blueprint = Blueprint('users', __name__, template_folder='templates')


@blueprint.route('/login', methods=['GET'])
def login():
    return render_response('login_form.tpl')


@blueprint.route('/login', methods=['POST'])
def process_login():
    password = post_param('password', template='login_form.tpl')
    email = post_param('email', template='login_form.tpl')
    user = log_in_user(email, password)
    if not user:
        abort(403, 'Login failed')
    return redirect(url_for('feed.view'))


@blueprint.route('/create', methods=['GET'])
def create_form():
    return render_response('create_form.tpl')


@blueprint.route('/create', methods=['POST'])
def create():
    """
    Create a new User (sign-up).
    """
    name = post_param('name', template='create_form.tpl')
    password = post_param('password', template='create_form.tpl')
    email = post_param('email', template='create_form.tpl')

    my_user = models.User()
    my_user.email = email
    my_user.contact.realname = name
    my_user.generate_keypair(password)
    my_user.activate()  # FIXME
    db.session.commit()
    return render_response('user_created.tpl')


@blueprint.route('/logout', methods=['GET'])
def logout():
    session['key'] = None
    session['user_id'] = None
    return render_response('logout.tpl')


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
    return render_response('activation_success.tpl')


@blueprint.route('/info', methods=['GET'])
def info():
    user = logged_in_user()
    if not user:
        abort(401, 'Not logged in')

    return render_response('edit.tpl', json_user(user))


def json_user(user):
    data = {
        'id': user.id,
        'email': user.email,
    }
    data.update(json_contact(user.contact))
    return data


@blueprint.route('/info', methods=['POST'])
def edit():
    from pyaspora.post.models import Post
    user = logged_in_user()
    if not user:
        abort(401, 'Not logged in')

    bio = post_param('bio', template='edit.tpl')

    p = Post(author=user.contact)
    db.session.add(p)

    p.add_part(
        order=0,
        inline=True,
        mime_part=MimePart(
            body=json.dumps({
                'fields_changed': ['bio']
            }).encode('utf-8'),
            type='application/x-pyaspora-profile-update',
            text_preview='{} updated their profile'.format(
                user.contact.realname),
        )
    )

    bio_part = MimePart(body=b'', type='text/plain', text_preview=bio)
    p.add_part(
        order=1,
        inline=True,
        mime_part=bio_part,
    )

    user.contact.bio = bio_part
    db.session.add(user.contact)

    p.share_with([user.contact])

    db.session.commit()
    return redirect(url_for('contacts.profile', contact_id=user.contact.id))
