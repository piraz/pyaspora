from flask import Blueprint, url_for

from pyaspora.contact.models import Contact
from pyaspora.contact.views import json_contact
from pyaspora.database import db
from pyaspora.utils.rendering import abort, redirect, render_response
from pyaspora.user.session import logged_in_user
from pyaspora.user.views import json_user
from pyaspora.roster.models import Subscription, SubscriptionGroup

blueprint = Blueprint('roster', __name__, template_folder='templates')


@blueprint.route('/edit', methods=['GET'])
def view():
    user = logged_in_user()
    if not user:
        abort(401, 'Not logged in')

    data = json_user(user)

    data['friends'] = [json_group(g) for g in user.groups]

    return render_response('friend_list.tpl', data)


def json_group(g, user):
    data = {
        'name': g.name,
        'actions': {
            'edit': 'FIXME',
            'delete': None
        },
        'contacts': [json_contact(s.contact, user) for s in g.subscriptions]
    }
    if not g.subscriptions:
        data['action']['edit'] = 'FIXME'
    return data


@blueprint.route('/subscribe/<int:contact_id>', methods=['POST'])
def subscribe(contact_id):
    user = logged_in_user()
    if not user:
        abort(401, 'Not logged in')

    contact = Contact.get(contact_id)
    if not contact:
        abort(404, 'No such contact', force_status=True)

    contact.subscribe(user)
    db.session.commit()
    return redirect(url_for('contacts.profile', contact_id=user.contact.id))


@blueprint.route('/unsubscribe/<int:contact_id>', methods=['POST'])
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

