"""
Actions/display relating to Contacts. These may be locally-mastered (who
can also do User actions), but they may be Contacts on other nodes using
cached information.
"""

from flask import Blueprint, make_response, url_for

from pyaspora.utils.rendering import abort, render_response
from pyaspora.contact import models

blueprint = Blueprint('contacts', __name__, template_folder='templates')

@blueprint.route('/<int:contact_id>/avatar', methods=['GET'])
def avatar(contact_id):
    """
    Display the photo (or other media) that represents a Contact.
    """
    contact = models.Contact.get(contact_id)
    if not contact:
        abort(404, 'No such contact', force_status=True)

    part = contact.avatar
    if not part:
        abort(404, 'Contact has no avatar', force_status=True)

    response = make_response(part.body)
    response.headers['Content-Type'] = part.type
    return response

@blueprint.route('/<int:contact_id>/profile', methods=['GET'])
def profile(contact_id):
    contact = models.Contact.get(contact_id)
    if not contact:
        abort(404, 'No such contact', force_status=True)
    
    data = contact_repr(contact)
    data['feed'] = []
    return render_response('profile.tpl', data)

def contact_repr(contact):
    resp = {
        'id': contact.id,
        'link': url_for('.profile', contact_id=contact.id, _external=True),
        'name': contact.realname,
        'bio': '',
        'avatar': None
    }
    if contact.avatar:
        resp['avatar'] = url_for('.avatar', contact_id=contact.id, _external=True)
        
    if contact.bio:
        resp['bio'] = contact.bio.text_preview
        
    return resp

# class Contact:
# 
#     @cherrypy.expose
#     def profile(self, username, full=None, perspective=None):
#         """
#         Display the "feed" for a Contact.
#         """
#         # Don't want a visitor to cause us to do lots of network access
#         should_import = User.logged_in()
# 
#         contact = model.Contact.get_by_username(
#             username, try_import=should_import)
# 
#         if not contact:
#             return view.denied(status=404)
# 
#         if should_import:
#             session.commit()  # in case imported
# 
#         posts = contact.feed
#         posts = [p.post for p in posts if p.post.parent is None]
#         formatted_posts = Post.format(posts, show_all=full)
# 
#         bio = None
#         if contact.bio:
#             try:
#                 bio = contact.bio.render_as('text/plain', inline=True)
#             except:
#                 pass
# 
#         logged_in_user = User.logged_in()
#         can_remove = False
#         can_add = False
#         can_post = False
# 
#         if not full:
#             full = (logged_in_user and logged_in_user.contact.id == contact.id)
# 
#         if logged_in_user:
#             can_remove = logged_in_user.subscribed_to(contact)
#             can_add = (not(can_remove) and
#                        logged_in_user.contact.id != contact.id)
#             can_post = (can_remove or logged_in_user.contact.id == contact.id)
# 
#         return view.Contact.profile(
#             contact=contact,
#             posts=formatted_posts,
#             can_add=can_add,
#             can_remove=can_remove,
#             can_post=can_post,
#             logged_in=logged_in_user,
#             bio=bio
#         )
# 
#     @cherrypy.expose
#     def find(self, search_term=None):
#         """
#         Search for a contact
#         """
#         pass
# 
#     @cherrypy.expose
#     def subscribe(self, contactid, subtype='friend'):
#         """
#         Subscribe (form a friendship of some sort) with a Contact. This is a
#         one-way relationship.
#         """
#         user = User.logged_in(required=True)
#         contact = model.Contact.get(contactid)
#         if not contact:
#             return view.denied(status=404, reason='Contact cannot be found')
#         contact.subscribe(user, subtype=subtype)
#         session.commit()
#         raise cherrypy.HTTPRedirect("/contact/profile?username={}".format(
#             quote_plus(contact.username)))
# 
#     @cherrypy.expose
#     def unsubscribe(self, contactid):
#         """
#         "Unfriend" a contact.
#         """
#         user = User.logged_in(required=True)
#         contact = model.Contact.get(contactid)
#         if not contact or not user.subscribed_to(contact):
#             return view.denied(status=404,
#                                reason='Subscription cannot be found')
#         contact.unsubscribe(user)
#         session.commit()
#         raise cherrypy.HTTPRedirect("/contact/friends?contactid={}".format(
#             user.contact.id))
# 
#     @cherrypy.expose
#     def friends(self, contactid):
#         """
#         Show a Contact's friends/subscriptions list.
#         """
#         user = User.logged_in()
#         contact = model.Contact.get(contactid)
#         if not contact:
#             return view.denied(status=404, reason='Contact cannot be found')
#         is_friends_with = (user and user.subscribed_to(contact))
#         public_view = not(user and user.contact.id == contact.id)
#         return view.Contact.friend_list(
#             contact=contact,
#             public_view=public_view,
#             is_friends_with=is_friends_with,
#             logged_in=user
#         )
# 
# 
# 
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


