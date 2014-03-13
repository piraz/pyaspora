from __future__ import absolute_import

from flask import Blueprint, request, url_for
from json import dumps
from sqlalchemy.sql import and_, not_

from pyaspora.content.models import MimePart
from pyaspora.content.rendering import render, renderer_exists
from pyaspora.contact.models import Contact
from pyaspora.contact.views import json_contact
from pyaspora.database import db
from pyaspora.post.models import Post, PostPart, Share
from pyaspora.post.targets import target_list, targets_by_name
from pyaspora.utils.rendering import abort, add_logged_in_user_to_data, \
    redirect, render_response
from pyaspora.utils.validation import check_attachment_is_safe, post_param
from pyaspora.user.session import require_logged_in_user
from pyaspora.tag.models import PostTag, Tag
from pyaspora.tag.views import json_tag

blueprint = Blueprint('posts', __name__, template_folder='templates')


def _get_cached(cache, entry_type, entry_id):
    if entry_id not in cache[entry_type]:
        cache[entry_type][entry_id] = {'id': entry_id}
    return cache[entry_type][entry_id]


def _base_cache():
    return {
        'contact': {},
        'post': {}
    }


def json_posts(posts_and_shares, viewing_as=None):
    """
    Run a list of (post, share) pairs through json_post, giving a list
    of for-serialisation views of Posts. This call is more efficient than
    calling json_post() repeatedly as data is cached.
    """
    cache = _base_cache()
    res = [
        json_post(p, viewing_as, s, cache=cache)
        for p, s in posts_and_shares
    ]
    _fill_cache(cache)
    return res


def json_post(post, viewing_as=None, share=None, children=True, cache=None):
    """
    Turn a Post in sensible representation for serialisation, from the view of
    Contact 'viewing_as', or the public if not provided. If a Share is
    provided then additional actions are provided. If 'children' is False then
    child Posts of this Post will not be fetched.
    """
    c = cache or _base_cache()

    sorted_children = sorted(post.viewable_children(viewing_as),
                             key=lambda p: p.created_at)
    data = _get_cached(c, 'post', post.id)
    data.update({
        'id': post.id,
        'author': _get_cached(c, 'contact', post.author_id),
        'parts': [],
        'children': None,
        'created_at': post.created_at.isoformat(),
        'actions': {
            'share': None,
            'comment': None,
            'hide': None,
            'make_public': None,
            'unmake_public': None,
        },
        'tags': [],
        'shares': None
    })
    if children:
        data['children'] = [
            json_post(
                p,
                viewing_as,
                p.shared_with(viewing_as) if viewing_as else None,
                cache=c
            ) for p in sorted_children
        ]
    if viewing_as:
        data['actions']['comment'] = url_for('posts.comment',
                                             post_id=post.id, _external=True)
        if viewing_as.id != post.author_id:
            data['actions']['share'] = \
                url_for('posts.share', post_id=post.id, _external=True)

        if share and viewing_as and share.contact_id == viewing_as.id:
            data['actions']['hide'] = url_for('posts.hide',
                                              post_id=post.id, _external=True)
            if share.public and post.can_change_privacy(False):
                data['actions']['unmake_public'] = \
                    url_for('posts.set_public',
                            post_id=post.id, toggle='0', _external=True)
            elif post.can_change_privacy(True):
                data['actions']['make_public'] = \
                    url_for('posts.set_public',
                            post_id=post.id, toggle='1', _external=True)

    if not cache:
        _fill_cache(c, bool(share))

    return data


def _fill_cache(c, show_shares=False):
    # Fill the cache in bulk, which will also fill the entries
    post_ids = c['post'].keys()
    for post_tag in PostTag.get_tags_for_posts(post_ids):
        c['post'][post_tag.post_id]['tags'].append(json_tag(post_tag.tag))
    post_parts = PostPart.get_parts_for_posts(post_ids). \
        order_by(PostPart.order)
    for post_part in post_parts:
        c['post'][post_part.post_id]['parts'].append(json_part(post_part))
    if show_shares:
        for post_share in Share.get_for_posts(post_ids):
            post_id = post_share.post_id
            if not c['post'][post_id]['shares']:
                c['post'][post_id]['shares'] = []
            c['post'][post_id]['shares'].append(
                json_share(post_share, cache=c)
            )
    if c['contact']:
        for contact in Contact.get_many(c['contact'].keys()):
            c['contact'][contact.id].update(json_contact(contact))


def json_share(share, cache=None):
    """
    Turn a Share into a sensible format for serialisation.
    """
    contact_repr = _get_cached(cache, 'contact', share.contact_id) if cache \
        else json_contact(share.contact)
    return {
        'contact': contact_repr,
        'shared_at': share.shared_at.isoformat(),
        'public': share.public
    }


def json_part(part):
    """
    Turn a PostPart into a sensible format for serialisation.
    """
    url = url_for('content.raw', part_id=part.mime_part.id, _external=True)
    return {
        'inline': part.inline,
        'mime_type': part.mime_part.type,
        'text_preview': part.mime_part.text_preview,
        'link': url,
        'body': {
            'text': render(part, 'text/plain', url),
            'html': render(part, 'text/html', url),
        }
    }


@blueprint.route('/<int:post_id>/share', methods=['GET'])
@require_logged_in_user
def share(post_id, _user):
    """
    Form to share an existing Post with more Contacts.
    """
    post = Post.get(post_id)
    if not post:
        abort(404, 'No such post', force_status=True)
    if not post.has_permission_to_view(_user.contact):
        abort(403, 'Forbidden')

    data = _base_create_form(_user)

    data.update({
        'relationship': {
            'type': 'share',
            'object': json_post(post, children=False),
            'description': 'Share this item'
        },
        'default_target': {
            'type': 'all_friends',
            'id': None
        }
    })
    return render_response('posts_create_form.tpl', data)


@blueprint.route('/<int:post_id>/comment', methods=['GET'])
@require_logged_in_user
def comment(post_id, _user):
    """
    Comment on (reply to) an existing Post.
    """
    post = Post.get(post_id)
    if not post:
        abort(404, 'No such post', force_status=True)
    if not post.has_permission_to_view(_user.contact):
        abort(403, 'Forbidden')

    data = _base_create_form(_user, post)

    data.update({
        'relationship': {
            'type': 'comment',
            'object': json_post(post, children=False),
            'description': 'Comment on this item'
        }
    })

    return render_response('posts_create_form.tpl', data)


@require_logged_in_user
def _get_share_for_post(post_id, _user):
    share = db.session.query(Share).filter(and_(
        Share.contact == _user.contact,
        Share.post_id == post_id,
        not_(Share.hidden))).first()
    if not share:
        abort(403, 'Not available')

    return share


@blueprint.route('/<int:post_id>/hide', methods=['POST'])
def hide(post_id):
    """
    Hide an existing Post from the user's wall and profile.
    """
    share = _get_share_for_post(post_id)

    share.hidden = True
    db.session.add(share)
    db.session.commit()

    return redirect(url_for('feed.view', _external=True))


@blueprint.route('/<int:post_id>/set_public/<int:toggle>', methods=['POST'])
def set_public(post_id, toggle):
    """
    Make the Post appear-on/disappear-from the User's public wall. If toggle
    is True then the post will appear.
    """
    share = _get_share_for_post(post_id)
    toggle = bool(toggle)

    if not share.post.can_change_privacy(toggle):
        abort(403, 'Not available')

    if share.public != toggle:
        share.public = toggle
        db.session.add(share)
        if toggle:
            # If it's going public, it'll be visible to more people
            share.post.thread_modified()
            db.session.add(share.post)
        db.session.commit()

    return redirect(url_for('feed.view', _external=True))


def _base_create_form(user, parent=None):
    if parent:
        targets = (
            t for t in target_list
            if t.permitted_for_reply(user, parent)
        )
        if parent.diasp:
            targets = (
                t for t in targets
                if parent.diasp.can_reply_with(t)
            )
    else:
        targets = (
            t for t in target_list
            if t.permitted_for_new(user)
        )

    data = {
        'next': url_for('.create', _external=True),
        'targets': [t.json_target(user, parent) for t in targets],
        'use_advanced_form': False
    }
    add_logged_in_user_to_data(data, user)
    return data


@blueprint.route('/create', methods=['GET'])
@require_logged_in_user
def create_form(_user):
    """
    Start a new Post.
    """
    data = _base_create_form(_user)
    data['use_advanced_form'] = True
    if request.args.get('target_type') and request.args.get('target_id'):
        data['default_target'] = {
            'type': request.args['target_type'],
            'id': request.args['target_id'],
        }
    return render_response('posts_create_form.tpl', data)


@blueprint.route('/create', methods=['POST'])
@require_logged_in_user
def create(_user):
    """
    Create a new Post and Share it with the selected Contacts.
    """
    body = post_param('body')
    relationship = {
        'type': post_param('relationship_type', optional=True),
        'id': post_param('relationship_id', optional=True),
    }

    target = {
        'type': post_param('target_type'),
        'id': post_param('target_id', optional=True),
    }

    assert(target['type'] in targets_by_name)

    # Loathe inflexible HTML forms
    if target['id'] is None:
        target['id'] = post_param(
            'target_%s_id' % target['type'], optional=True)

    if relationship['type']:
        post = Post.get(relationship['id'])
        if not post:
            abort(404, 'No such post', force_status=True)
        if not post.has_permission_to_view(_user.contact):
            abort(403, 'Forbidden')
        relationship['post'] = post

    post = Post(author=_user.contact)
    body_part = MimePart(type='text/x-markdown', body=body.encode('utf-8'),
                         text_preview=None)

    topics = post_param('tags', optional=True)
    if topics:
        post.tags = Tag.parse_line(topics, create=True)

    if relationship['type'] == 'comment':
        post.parent = relationship['post']
        post.add_part(body_part, order=0, inline=True)
    elif relationship['type'] == 'share':
        shared = relationship['post']
        share_part = MimePart(
            type='application/x-pyaspora-share',
            body=dumps({
                'post': {'id': shared.id},
                'author': {
                    'id': shared.author_id,
                    'name': shared.author.realname,
                }
            }).encode('utf-8'),
            text_preview="shared {0}'s post".format(shared.author.realname)
        )
        post.add_part(share_part, order=0, inline=True)
        post.add_part(body_part, order=1, inline=True)
        order = 1
        for part in shared.parts:
            if part.mime_part.type != 'application/x-pyaspora-share':
                order += 1
                post.add_part(part.mime_part, inline=part.inline, order=order)
        if not post.tags:
            post.tags = shared.tags
    else:  # Naked post
        post.add_part(body_part, order=0, inline=True)
        attachment = request.files.get('attachment', None)
        if attachment and attachment.filename:
            check_attachment_is_safe(attachment)
            attachment_part = MimePart(
                type=attachment.mimetype,
                body=attachment.stream.read(),
                text_preview=attachment.filename
            )
            post.add_part(attachment_part, order=1,
                          inline=bool(renderer_exists(attachment.mimetype)))

    post.thread_modified()

    # Sigh, need an ID for the post for making shares
    db.session.add(post)
    db.session.commit()

    targets_by_name[target['type']].make_shares(post, target['id'])
    db.session.commit()

    data = json_post(post)
    return redirect(url_for('feed.view', _external=True), data_structure=data)
