import json
from flask import Blueprint, url_for

from pyaspora.contact.models import Contact
from pyaspora.contact.views import json_contact
from pyaspora.content.models import MimePart
from pyaspora.database import db
from pyaspora.user.session import logged_in_user
from pyaspora.user.views import json_user
from pyaspora.utils.rendering import abort, add_logged_in_user_to_data, \
    redirect, render_response
from pyaspora.utils.validation import post_param
from pyaspora.roster.models import Subscription, SubscriptionGroup

blueprint = Blueprint('roster', __name__, template_folder='templates')


@blueprint.route('/edit', methods=['GET'])
def view():
    user = logged_in_user()
    if not user:
        abort(401, 'Not logged in')

    data = json_user(user)

    data['actions']['create_group'] = url_for(
        'roster.create_group', _external=True)
    data['groups'] = [json_group(g, user) for g in user.groups]

    add_logged_in_user_to_data(data, user)

    return render_response('roster_view.tpl', data)


def json_group(g, user):
    data = {
        'id': g.id,
        'name': g.name,
        'actions': {
            'edit': url_for('.edit_group_form', group_id=g.id, _external=True),
            'delete': None,
            'rename': url_for('.rename_group', group_id=g.id, _external=True)
        },
        'contacts': [json_contact(s.contact, user) for s in g.subscriptions]
    }
    if not g.subscriptions:
        data['actions']['delete'] = url_for(
            '.delete_group', group_id=g.id, _external=True)
    return data


@blueprint.route('/groups/create', methods=['POST'])
def create_group():
    user = logged_in_user()
    if not user:
        abort(401, 'Not logged in')

    name = post_param('name')

    db.session.add(SubscriptionGroup(user=user, name=name))
    db.session.commit()

    return redirect(url_for('roster.view', _external=True))


@blueprint.route('/groups/<int:group_id>/edit', methods=['GET'])
def edit_group_form(group_id):
    user = logged_in_user()
    if not user:
        abort(401, 'Not logged in')

    group = SubscriptionGroup.get(group_id)
    if not(group) or group.user_id != user.id:
        abort(404, 'No such group')

    data = json_user(user)

    data['actions'].update({
        'create_group': url_for('roster.create_group', _external=True),
        'move_contacts': "fixme"
    })
    data.update({
        'group': json_group(group, user),
        'other_groups': [json_group(g, user)
                         for g in user.groups if g.id != group.id]
    })

    add_logged_in_user_to_data(data, user)

    return render_response('roster_edit_group.tpl', data)


@blueprint.route('/groups/<int:group_id>/rename', methods=['POST'])
def rename_group(group_id):
    user = logged_in_user()
    if not user:
        abort(401, 'Not logged in')

    group = SubscriptionGroup.get(group_id)
    if not(group) or group.user_id != user.id:
        abort(404, 'No such group')

    group.name = post_param('name')
    db.session.add(group)
    db.session.commit()

    return redirect(url_for('.view', _external=True))


@blueprint.route('/groups/<int:group_id>/delete', methods=['POST'])
def delete_group(group_id):
    user = logged_in_user()
    if not user:
        abort(401, 'Not logged in')

    group = SubscriptionGroup.get(group_id)
    if not(group) or group.user_id != user.id:
        abort(404, 'No such group')

    if group.subscriptions:
        abort(400, 'Only empty groups can be deleted')

    db.session.delete(group)
    db.session.commit()

    return redirect(url_for('.view', _external=True))


@blueprint.route('/contacts/<int:contact_id>/subscribe', methods=['POST'])
def subscribe(contact_id):
    from pyaspora.post.models import Post
    user = logged_in_user()
    if not user:
        abort(401, 'Not logged in')

    contact = Contact.get(contact_id)
    if not contact:
        abort(404, 'No such contact', force_status=True)

    contact.subscribe(user)

    p = Post(author=user.contact)
    db.session.add(p)

    p.add_part(
        order=0,
        inline=True,
        mime_part=MimePart(
            body=json.dumps({
                'from': user.contact.id,
                'to': contact.id,
            }).encode('utf-8'),
            type='application/x-pyaspora-subscribe',
            text_preview='{} subscribed to {}'.format(
                user.contact.realname, contact.realname),
        )
    )
    p.share_with([user.contact, contact])

    db.session.commit()
    return redirect(url_for('contacts.profile', contact_id=user.contact.id))


@blueprint.route('/contacts/<int:contact_id>/unsubscribe', methods=['POST'])
def unsubscribe(contact_id):
    user = logged_in_user()
    if not user:
        abort(401, 'Not logged in')

    contact = Contact.get(contact_id)
    if not contact:
        abort(404, 'No such contact', force_status=True)

    if not user.subscribed_to(contact):
        abort(400, 'Not subscribed')

    contact.unsubscribe(user)
    db.session.commit()
    return redirect(url_for('contacts.profile', contact_id=user.contact.id))



#     @cherrypy.expose
#     def groups(self, contactid, groups=None, newgroup=None):
#         """
#         Edit which SubscriptionGroups this Contact is in.
#         """
#         contact = model.Contact.get(contactid)
#         if not contact:
#             return view.denied(status=404, reason='No such user')
# 
#         user = User.logged_in(required=True)
# 
#         # Need to be logged in to create a post
# 
#         if not user.subscribed_to(contact):
#             return view.denied(status=400,
#                                reason='You are not subscribed to this contact')
# 
#         if groups:
#             subtype = user.subscribed_to(contact).type
# 
#             if not isinstance(groups, list):
#                 groups = [groups]
#             target_groups = set(groups)
# 
#             if newgroup:
#                 newgroup = newgroup.strip()
# 
#             if newgroup and 'new' in target_groups:
#                 new_group_obj = model.SubscriptionGroup.get_by_name(
#                     user, newgroup, create=True)
#                 session.add(new_group_obj)
#                 session.commit()
#                 target_groups.add(new_group_obj.id)
# 
#             for group in user.groups:
#                 if group.id in target_groups:
#                     group.add_contact(contact, subtype)
# 
#                 else:
#                     sub = group.has_contact(contact)
#                     if sub:
#                         session.delete(sub)
# 
#             session.commit()
# 
#             raise cherrypy.HTTPRedirect("/contact/friends?contactid={}".format(
#                 user.contact.id))
# 
#         group_status = dict([(g, g.has_contact(contact)) for g in user.groups])
#         return view.Contact.edit_groups(logged_in=user, contact=contact,
#                                         groups=group_status)


# class SubscriptionGroup:
#     """
#     Actions relating to a named group of friends/contacts (a "circle" in G+)
#     """
#     @cherrypy.expose
#     def rename(self, groupid, newname=None):
#         """
#         Give a group a new name.
#         """
#         if not newname:
#             return view.SubscriptionGroup.rename_form(
#                 group=group, logged_in=user)
# 
#         user = User.logged_in(required=True)
#         group = model.SubscriptionGroup.get(groupid)
#         if not group:
#             raise cherrypy.HTTPError(404)
#         if group.user_id != user.id:
#             raise cherrypy.HTTPError(403)
#         group.name = newname
#         session.commit()
#         raise cherrypy.HTTPRedirect("/contact/friends?contactid={}".format(
#             user.contact.id))
#         if newname:
#             group.name = newname
#             session.commit()
#             raise cherrypy.HTTPRedirect("/contact/friends?contactid={}".format(user.contact.id))
#         else:
#             return view.SubscriptionGroup.rename_form(group=group, logged_in=user)

