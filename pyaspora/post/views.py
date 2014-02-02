from flask import Blueprint, url_for
from sqlalchemy.sql import and_, not_

from pyaspora.content.rendering import render
from pyaspora.contact.views import json_contact
from pyaspora.database import db
from pyaspora.post.models import Share
from pyaspora.utils.rendering import abort, redirect
from pyaspora.user.session import logged_in_user

blueprint = Blueprint('posts', __name__, template_folder='templates')


def json_post(post, viewing_as=None, wall=False):
    sorted_parts = sorted(post.parts, key=lambda p: p.order)
    sorted_children = sorted(post.children, key=lambda p: p.created_at)
    data = {
        'id': post.id,
        'author': json_contact(post.author),
        'parts': [json_part(p) for p in sorted_parts],
        'children': [json_post(p) for p in sorted_children
                     if p.has_permission_to_view(viewing_as)],
        'created_at': post.created_at.isoformat(),
        'actions': {
            'share': None,
            'comment': None,
            'hide': None,
            'make_public': None,
            'unmake_public': None,
        }
    }
    if viewing_as:
        data['actions']['comment'] = url_for('posts.comment',
                                             post_id=post.id, _external=True)
        if viewing_as.id != post.author_id:
            data['actions']['share'] = \
                url_for('posts.share', post_id=post.id, _external=True)
        if wall:
            data['actions']['hide'] = url_for('posts.hide',
                                              post_id=post.id, _external=True)
            if wall.public:
                data['actions']['unmake_public'] = \
                    url_for('posts.set_public',
                            post_id=post.id, toggle='0', _external=True)
            else:
                data['actions']['make_public'] = \
                    url_for('posts.set_public',
                            post_id=post.id, toggle='1', _external=True)
    return data


def json_part(part):
    url = url_for('content.raw', part_id=part.mime_part.id, _external=True)
    return {
        'inline': part.inline,
        'mime_type': part.mime_part.type,
        'text_preview': part.mime_part.text_preview,
        'link': url,
        'body': {
            'raw': str(part.mime_part.body) if part.inline else None,
            'text': render(part, 'text/plain', url),
            'html': render(part, 'text/html', url),
        }
    }


@blueprint.route('/<int:post_id>/share', methods=['GET'])
def share(post_id):
    return "share"


@blueprint.route('/<int:post_id>/comment', methods=['GET'])
def comment(post_id):
    return "comment"


def _get_share_for_post(post_id):
    user = logged_in_user()
    if not user:
        abort(401, 'Not logged in')

    share = db.session.query(Share).filter(and_(
        Share.contact == user.contact,
        Share.post_id == post_id,
        not_(Share.hidden))).first()
    if not share:
        abort(403, 'Not available')

    return share

    
@blueprint.route('/<int:post_id>/hide', methods=['POST'])
def hide(post_id):
    share = _get_share_for_post(post_id)

    share.hidden = True
    db.session.add(share)
    db.session.commit()

    return redirect(url_for('feed.view', _external=True))


@blueprint.route('/<int:post_id>/set_public/<int:toggle>', methods=['POST'])
def set_public(post_id, toggle):
    share = _get_share_for_post(post_id)

    if share.public != toggle:
        share.public = toggle
        db.session.add(share)
        db.session.commit()

    return redirect(url_for('feed.view', _external=True))

# class Post:
#     @cherrypy.expose
#     def create(self, body=None, parent=None, share=None, share_level=None,
#                walls_too=False, **kwargs):
#         """
#         Create a new Post and put it on my wall. May also put it on friends
#         walls', depending on the Post's privacy level.
#         """
#         author = User.logged_in(required=True)
#         walls_too = bool(walls_too)
# 
#         share_with_options = {
#             'Groups': {"group-{}".format(g.id): g.name for g in author.groups},
#             'Contacts': {"friend-{}".format(f.id): f.realname
#                          for f in author.friends()},
#         }
#         for opt, subopt in share_with_options.items():
#             if not subopt:
#                 del share_with_options[opt]
#         share_with_options.update({
#             'Me': None,
#         })
#         if parent:
#             share_with_options.update({
#                 'PersonReplyingTo': None
#             })
# 
#         # If the mandatory fields aren't supplied, we are probably creating a
#         # new post
#         if not body:
#             return view.Post.create_form(parent=parent,
#                                          share_with_options=share_with_options)
# 
#         post = model.Post(author=author.contact)
# 
#         # figure out if this is a comment on another post
#         if parent:
#             parent_post = model.Post.get(parent)
#             # are we permitted to comment on it?
#             if not(parent_post) or not(self.permission_to_view(parent_post)):
#                 return view.denied(status=403)
#             if parent_post:
#                 post.parent = parent_post
# 
#         # prepare the MIME part and link it to the post
#         part = model.MimePart(type='text/plain', body=body.encode('utf-8'),
#                               text_preview=body)
#         post.add_part(part, inline=True, order=1)
# 
#         # post to author's wall
#         post.share_with([author.contact], show_on_wall=walls_too)
# 
#         if share_level.lower() == "group":
#             for g in author.groups:
#                 if kwargs.get('group-{}'.format(g.id)):
#                     post.share_with([s.contact for s in g.subscriptions],
#                                     show_on_wall=walls_too)
# 
#         if walls_too or share_level.lower() == 'contacts':
#             for f in author.friends():
#                 if share_level.lower() == 'contacts' and \
#                         kwargs.get('friend-{}'.format(f.id)):
#                     post.share_with([f], show_on_wall=walls_too)
#                 else:
#                     # If I post it publicly on author's wall, all the contacts
#                     # will see it, so ensure all the contacts get it.
#                     post.share_with([f], show_on_wall=False)
# 
#         if share_level.lower() == 'personreplyingto' and parent_post:
#             post.share_with([parent_post.author], show_on_wall=walls_too)
# 
#         # commit everything to get the Post ID
#         session.commit()
# 
#         # done
#         return view.Post.created(post=post)
# 
#     @classmethod
#     def format(cls, posts, all_parts=False, show_all=False):
#         """
#         Convert a list of posts into a series of text/{html,plain} parts for
#         web display.
#         """
#         formatted_posts = []
#         for post in posts:
#             to_display = []
#             if Post.permission_to_view(post):
#                 for link in post.parts:
#                     if link.inline:
#                         try:
#                             rendered = link.mime_part.render_as(
#                                 'text/html', inline=True)
#                             to_display.append(
#                                 {'type': 'text/html', 'body': rendered})
#                         except:
#                             rendered = link.mime_part.render_as(
#                                 'text/plain', inline=True)
#                             to_display.append(
#                                 {'type': 'text/plain', 'body': rendered})
#                     elif (show_all):
#                         to_display.append(
#                             {'type': 'text/plain', 'body': 'Attachment'})
#                 formatted_post = {'post': post, 'formatted_parts': to_display}
#                 child_posts = post.children
#                 if child_posts:
#                     shared_children = [p for p in child_posts]
#                     formatted_post['children'] = cls.format(
#                         shared_children, all_parts=all_parts, show_all=True)
#                 formatted_posts.append(formatted_post)
#         return formatted_posts
