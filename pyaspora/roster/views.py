from __future__ import absolute_import

from flask import Blueprint, request, url_for
from sqlalchemy.sql import and_

from pyaspora.contact.models import Contact
from pyaspora.contact.views import json_contact
from pyaspora.database import db
from pyaspora.user.session import require_logged_in_user
from pyaspora.user.views import json_user
from pyaspora.utils.rendering import abort, add_logged_in_user_to_data, \
    redirect, render_response
from pyaspora.utils.validation import post_param
from pyaspora.roster.models import Subscription, SubscriptionGroup

blueprint = Blueprint('roster', __name__, template_folder='templates')


def json_contact_with_groups(sub, user):
    result = json_contact(sub.to_contact, user)
    result['groups'] = [json_group(g, sub.to_contact) for g in sub.groups]
    return result


@blueprint.route('/edit', methods=['GET'])
@require_logged_in_user
def view(_user):
    subs = db.session.query(Subscription). \
        filter(Subscription.from_contact == _user.contact)
    data = {
        'subscriptions': [json_contact_with_groups(s, _user) for s in subs]
    }

    add_logged_in_user_to_data(data, _user)

    return render_response('roster_view.tpl', data)


def json_group(g, contact=None):
    data = {
        'id': g.id,
        'name': g.name,
        'link': url_for('roster.view_group',
                        group_id=g.id, _external=True),
        'actions': {
            'rename': url_for('roster.rename_group',
                              group_id=g.id, _external=True)
        },
    }
    if contact:
        data['actions']['remove_contact'] = url_for(
            'roster.remove_contact',
            group_id=g.id,
            contact_id=contact.id,
            _external=True
        )
    return data


@blueprint.route('/groups/<int:group_id>', methods=['GET'])
@require_logged_in_user
def view_group(group_id, _user):
    group = SubscriptionGroup.get(group_id)
    if not(group) or group.user_id != _user.id:
        abort(404, 'No such group')

    data = {
        'subscriptions': [
            json_contact_with_groups(s, _user)
            for s in group.subscriptions
        ],
        'group': json_group(group)
    }

    add_logged_in_user_to_data(data, _user)

    return render_response('roster_view_group.tpl', data)


@blueprint.route('/contacts/<int:contact_id>/edit', methods=['GET'])
@require_logged_in_user
def edit_contact_groups_form(contact_id, _user):
    contact = Contact.get(contact_id)
    if not contact:
        abort(404, 'No such contact')
    sub = _user.contact.subscribed_to(contact)
    if not sub:
        abort(404, 'No such contact')

    data = {
        'actions': {
            'save_groups': url_for(
                '.save_contact_groups',
                contact_id=contact.id,
                _external=True
            )
        },
        'subscription': json_contact_with_groups(sub, _user)
    }

    add_logged_in_user_to_data(data, _user)

    return render_response('roster_edit_group.tpl', data)


@blueprint.route('/groups/<int:group_id>/rename', methods=['POST'])
@require_logged_in_user
def rename_group(group_id, _user):
    group = SubscriptionGroup.get(group_id)
    if not(group) or group.user_id != _user.id:
        abort(404, 'No such group')

    group.name = post_param('name')
    if group.name_is_valid(group.name):
        db.session.add(group)
        db.session.commit()

    return redirect(url_for('.view', _external=True))


@blueprint.route(
    '/groups/<int:group_id>/remove_contact/<int:contact_id>',
    methods=['POST']
)
@require_logged_in_user
def remove_contact(group_id, contact_id, _user):
    group = SubscriptionGroup.get(group_id)
    if not(group) or group.user_id != _user.id:
        abort(404, 'No such group')

    new_list = [
        s for s in group.subscriptions
        if s.to_contact.id != contact_id
    ]
    group.subscriptions = new_list
    db.session.commit()

    if not new_list:
        db.session.delete(group)
        db.session.commit()

    return redirect(url_for('.view', _external=True))


@blueprint.route('/contacts/<int:contact_id>/subscribe', methods=['POST'])
@require_logged_in_user
def subscribe(contact_id, _user):
    contact = Contact.get(contact_id)
    if not contact:
        abort(404, 'No such contact', force_status=True)

    _user.contact.subscribe(contact)

    db.session.commit()
    return redirect(url_for('contacts.profile', contact_id=contact.id))


@blueprint.route('/contacts/<int:contact_id>/unsubscribe', methods=['POST'])
@require_logged_in_user
def unsubscribe(contact_id, _user):
    contact = Contact.get(contact_id)
    if not contact:
        abort(404, 'No such contact', force_status=True)

    if not _user.contact.subscribed_to(contact):
        abort(400, 'Not subscribed')

    _user.contact.unsubscribe(contact)
    db.session.commit()
    return redirect(url_for('contacts.profile', contact_id=contact.id))


@blueprint.route('/contacts/<int:contact_id>/edit', methods=['POST'])
@require_logged_in_user
def save_contact_groups(contact_id, _user):
    contact = Contact.get(contact_id)
    if not contact:
        abort(404, 'No such contact', force_status=True)

    sub = _user.contact.subscribed_to(contact)
    if not sub:
        abort(400, 'Not subscribed')

    groups = post_param(
        'groups',
        template='roster_edit_group.tpl',
        optional=True
    ) or ''
    new_groups = {
        g.name: g for g in
        SubscriptionGroup.parse_line(groups, create=True, user=_user)
    }
    old_groups = {g.name: g for g in sub.groups}

    for group_name, group in old_groups.items():
        if group_name not in new_groups:
            other_members = [
                s for s in group.subscriptions
                if s.to_id != contact.id
            ]
            if not other_members:
                db.session.delete(group)
    sub.groups = list(new_groups.values())
    db.session.add(sub)
    db.session.commit()

    return redirect(url_for('.view', _external=True))
