"""
Actions/display relating to Contacts. These may be locally-mastered (who
can also do User actions), but they may be Contacts on other nodes using
cached information.
"""

from __future__ import absolute_import

from base64 import b64encode
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from flask import abort, Blueprint, current_app, jsonify, make_response, \
    request, url_for
from json import dumps
from lxml import etree
from sqlalchemy.sql import desc
from traceback import format_exc
try:
    from urllib.parse import urlsplit
except:
    from urlparse import urlsplit

from pyaspora import db
from pyaspora.contact.models import Contact
from pyaspora.diaspora.actions import process_incoming_message
from pyaspora.diaspora.models import DiasporaContact, DiasporaPost, \
    MessageQueue
from pyaspora.diaspora.protocol import DiasporaMessageParser
from pyaspora.post.models import Post, Share
from pyaspora.user.models import User
from pyaspora.user.session import require_logged_in_user
from pyaspora.utils.rendering import add_logged_in_user_to_data, \
    redirect, render_response, send_xml

blueprint = Blueprint('diaspora', __name__, template_folder='templates')


@blueprint.route('/.well-known/host-meta', methods=['GET'])
def host_meta():
    """
    Return a WebFinder host-meta, which points the client to the end-point
    for webfinger querying.
    """
    ns = 'http://docs.oasis-open.org/ns/xri/xrd-1.0'
    doc = etree.Element("{%s}XRD" % ns, nsmap={None: ns})
    etree.SubElement(
        doc, "Link",
        rel='lrdd',
        template=url_for(
            '.webfinger',
            contact_addr='',
            _external=True
        ) + '{uri}',
        type='application/xrd+xml'
    )
    return send_xml(doc)


@blueprint.route('/diaspora/webfinger/<string:contact_addr>', methods=['GET'])
def webfinger(contact_addr):
    """
    Returns the Webfinger profile for a contact called <contact> (in
    "user@host" form).
    """
    contact_id, _ = contact_addr.split('@')
    c = Contact.get(int(contact_id))
    if not c or not c.user or not c.user.activated:
        abort(404, 'No such contact')
    diasp = DiasporaContact.get_for_contact(c)

    ns = 'http://docs.oasis-open.org/ns/xri/xrd-1.0'
    doc = etree.Element("{%s}XRD" % ns, nsmap={None: ns})
    etree.SubElement(doc, "Subject").text = "acct:%s" % diasp.username
    etree.SubElement(doc, "Alias").text = \
        '"{0}"'.format(url_for('index', _external=True))
    etree.SubElement(
        doc, "Link",
        rel='http://microformats.org/profile/hcard',
        type='text/html',
        href=url_for('.hcard', guid=diasp.guid, _external=True)
    )
    etree.SubElement(
        doc, "Link",
        rel='http://joindiaspora.com/seed_location',
        type='text/html',
        href=url_for('index', _external=True)
    )
    etree.SubElement(
        doc, "Link",
        rel='http://joindiaspora.com/guid',
        type='text/html',
        href=diasp.guid
    )
    etree.SubElement(
        doc, "Link",
        rel='http://webfinger.net/rel/profile-page',
        type='text/html',
        href=url_for('contacts.profile', contact_id=c.id, _external=True)
    )
    etree.SubElement(
        doc, "Link",
        rel='http://schemas.google.com/g/2010#updates-from',
        type='application/atom+xml',
        href=url_for('contacts.feed', contact_id=c.id, _external=True)
    )
    etree.SubElement(
        doc, "Link",
        rel='diaspora-public-key',
        type='RSA',
        href=b64encode(c.public_key.encode('ascii'))
    )

    return send_xml(doc)


@blueprint.route('/diaspora/hcard/<string:guid>', methods=['GET'])
def hcard(guid):
    """
    Returns the hCard for the User with GUID <guid>. I would have
    preferred to use the primary key, but the protocol insists on
    fetch-by-GUID.
    """
    diasp = DiasporaContact.get_by_guid(guid)
    if diasp is None or not diasp.contact.user:
        abort(404, 'No such contact')
    c = diasp.contact

    ns = 'http://www.w3.org/1999/xhtml'
    doc = etree.Element("{%s}div" % ns, nsmap={None: ns}, id="content")
    etree.SubElement(doc, "h1").text = c.realname
    content_inner = etree.SubElement(
        doc,
        'div',
        **{'class': "content_inner"}
    )
    author = etree.SubElement(
        content_inner,
        'div',
        id="i",
        **{'class': "entity_profile vcard author"}
    )

    etree.SubElement(author, "h2").text = "User profile"

    dl = etree.SubElement(author, 'dl', **{'class': "entity_nickname"})
    etree.SubElement(dl, 'dt').text = 'Nickname'
    dd = etree.SubElement(dl, 'dd')
    etree.SubElement(
        dd,
        'a',
        rel='me',
        href=url_for('index'),
        **{'class': "nickname url uid"}
    ).text = c.realname

    dl = etree.SubElement(author, 'dl', **{'class': "entity_fn"})
    etree.SubElement(dl, 'dt').text = 'Full name'
    dd = etree.SubElement(dl, 'dd').text = c.realname

    dl = etree.SubElement(author, 'dl', **{'class': "entity_url"})
    etree.SubElement(dl, 'dt').text = 'URL'
    dd = etree.SubElement(dl, 'dd')
    etree.SubElement(
        dd,
        'a',
        id='pod_location',
        rel='me',
        href=url_for('index', _external=True),
        **{'class': "url"}
    ).text = url_for('index', _external=True)

    # FIXME - need to resize photos
    photos = {
        "entity_photo": "300px",
        "entity_photo_medium": "100px",
        "entity_photo_small": "50px"
    }
    for k, v in photos.items():
        src = diasp.photo_url()
        dl = etree.SubElement(author, "dl", **{'class': k})
        etree.SubElement(dl, "dt").text = "Photo"
        dd = etree.SubElement(dl, "dd")
        etree.SubElement(
            dd,
            'img',
            height=v,
            width=v,
            src=src,
            **{'class': "photo avatar"}
        )

    dl = etree.SubElement(author, 'dl', **{'class': "entity_searchable"})
    etree.SubElement(dl, 'dt').text = 'Searchable'
    dd = etree.SubElement(dl, 'dd')
    etree.SubElement(dd, 'a', **{'class': "searchable"}).text = 'true'

    return send_xml(doc, content_type='text/html')


@blueprint.route('/receive/users/<string:guid>/', methods=['POST'])
def receive(guid):
    """
    Receive a Salmon Slap and save it for when the user logs in.
    """
    diasp = DiasporaContact.get_by_guid(guid)
    if diasp is None or not diasp.contact.user:
        abort(404, 'No such contact')

    queue_item = MessageQueue()
    queue_item.local_user = diasp.contact.user
    queue_item.remote = None
    queue_item.format = MessageQueue.INCOMING
    queue_item.body = request.form['xml'].encode('ascii')
    db.session.add(queue_item)
    db.session.commit()

    diasp.contact.user.notify_event()

    return 'OK'


@blueprint.route('/receive/public', methods=['POST'])
def receive_public():
    """
    Receive a public Salmon Slap and process it now.
    """
    dmp = DiasporaMessageParser(DiasporaContact.get_by_username)
    ret, c_from = dmp.decode(request.form['xml'], None)
    try:
        process_incoming_message(ret, c_from, None)
        return 'OK'
    except Exception:
        err = format_exc()
        current_app.logger.error(err)
        db.session.expunge_all()
        queue_item = MessageQueue()
        queue_item.local_user = None
        queue_item.remote = None
        queue_item.format = MessageQueue.PUBLIC_INCOMING
        queue_item.body = request.form['xml'].encode('ascii')
        queue_item.error = err.encode('utf-8')
        db.session.add(queue_item)
        return 'Error', 400
    finally:
        db.session.commit()


@blueprint.route('/people/<string:guid>', methods=['GET'])
def json_feed(guid):
    """
    Look up the User identified by GUID and return the User's public feed
    as Diaspora-style JSON.
    """
    contact = DiasporaContact.get_by_guid(guid)
    if not(contact and contact.contact.user):
        abort(404, 'No such contact', force_status=True)

    feed_query = Post.Queries.public_wall_for_contact(contact.contact)
    feed = db.session.query(Post).join(Share).filter(feed_query). \
        order_by(desc(Post.thread_modified_at)). \
        group_by(Post.id).limit(99)

    ret = []
    for post in feed:
        text = DiasporaPost.get_for_post(post, commit=False).as_text()
        rep = {
            "author": {
                "diaspora_id": contact.username,
                "name": contact.contact.realname,
                "guid": contact.guid,
            },
            "created_at": post.created_at.isoformat(),
            "text": text,
            "public": True,
            "post_type": "StatusMessage",
            "guid": post.diasp.guid,
            "interacted_at": post.root().thread_modified_at.isoformat(),
            "provider_display_name": None,
        }
        ret.append(rep)

    return jsonify(response)


@blueprint.route('/diaspora/run_queue', methods=['GET'])
@require_logged_in_user
def run_queue(_user):
    start = datetime.now()
    retry = True
    processed = int(request.args.get('processed', 0))
    delta = 10 if processed else 3  # Small first batch
    while datetime.now() < start + timedelta(seconds=delta):
        if not MessageQueue.has_pending_items(_user):
            retry = False
            break
        MessageQueue.process_incoming_queue(_user, max_items=1)
        processed += 1

    data = {
        'count': processed,
        'next': url_for('.run_queue', processed=processed, _external=True)
    }
    add_logged_in_user_to_data(data, _user)

    if retry:
        resp = make_response(render_response('diaspora_queue.tpl', data))
        resp.headers['Refresh'] = '1;{0}'.format(data['next'])
        return resp
    else:
        return redirect(url_for('feed.view'))


@blueprint.route('/diaspora/run_public_queue', methods=['GET'])
@require_logged_in_user
def run_public_queue(_user):
    queue_items = db.session.query(MessageQueue).filter(
        MessageQueue.Queries.pending_public_items()
    ).order_by(MessageQueue.created_at)
    for qi in queue_items:
        if qi.error:
            break

        try:
            qi.process_incoming()
        except Exception:
            err = format_exc()
            qi.error = err.encode('utf-8')
            current_app.logger.error(err)
            db.session.add(qi)
            db.session.commit()
            break
        else:
            db.session.delete(qi)
            db.session.commit()
    return redirect(url_for('feed.view'))


@blueprint.route('/statistics.json', methods=['GET'])
def stats():
    return jsonify({
        'name': '{0} Pyaspora'.format(urlsplit(request.url)[1]),
        'version': '0.x',
        'registrations_open': current_app.config.get('ALLOW_CREATION', False),
        'total_users': db.session.query(User).count(),
        'active_users_halfyear':
        db.session.query(User).join(Contact).join(Post).filter(
            Post.created_at > datetime.now() - relativedelta(months=6)
        ).group_by(User.id).count(),
        'active_users_monthly':
        db.session.query(User).join(Contact).join(Post).filter(
            Post.created_at > datetime.now() - relativedelta(months=1)
        ).group_by(User.id).count(),
        'local_posts': db.session.query(User).join(Contact).join(Post).count()
    })
