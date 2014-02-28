"""
Actions/display relating to Contacts. These may be locally-mastered (who
can also do User actions), but they may be Contacts on other nodes using
cached information.
"""

import base64
import json
from flask import abort, Blueprint, request, url_for
from lxml import etree

from pyaspora import db
from pyaspora.contact.models import Contact
from pyaspora.diaspora.models import DiasporaContact, MessageQueue
from pyaspora.diaspora.utils import process_incoming_queue
from pyaspora.user.session import require_logged_in_user
from pyaspora.utils.rendering import redirect, send_xml

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
    if c is None or not c.user:
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
        href=base64.b64encode(c.public_key.encode('ascii'))
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
    print("diasp={}".format(diasp))
    if diasp is None or not diasp.contact.user:
        abort(404, 'No such contact')
    c = diasp.contact

    ns = 'http://www.w3.org/1999/xhtml'
    doc = etree.Element("{%s}div" % ns, nsmap={None: ns}, id="content")
    etree.SubElement(doc, "h1").text = c.realname
    content_inner = etree.SubElement(
        doc, 'div', **{'class': "content_inner"})
    author = etree.SubElement(
        content_inner, 'div', id="i", **{
            'class': "entity_profile vcard author"})

    etree.SubElement(author, "h2").text = "User profile"

    dl = etree.SubElement(author, 'dl', **{'class': "entity_nickname"})
    etree.SubElement(dl, 'dt').text = 'Nickname'
    dd = etree.SubElement(dl, 'dd')
    etree.SubElement(
        dd, 'a', rel='me', href=url_for('index'), **{
            'class': "nickname url uid"}
    ).text = c.realname

    dl = etree.SubElement(author, 'dl', **{'class': "entity_fn"})
    etree.SubElement(dl, 'dt').text = 'Full name'
    dd = etree.SubElement(dl, 'dd').text = c.realname

    dl = etree.SubElement(author, 'dl', **{'class': "entity_url"})
    etree.SubElement(dl, 'dt').text = 'URL'
    dd = etree.SubElement(dl, 'dd')
    etree.SubElement(
        dd, 'a', id='pod_location', rel='me',
        href=url_for('index', _external=True),
        **{'class': "url"}).text = url_for('index', _external=True)

    # FIXME - need to resize photos. Having no photos causes Diaspora to
    # crash, so we need to return *something* in all cases.
    photos = {
        "entity_photo": "300px",
        "entity_photo_medium": "100px",
        "entity_photo_small": "50px"
    }
    for k, v in photos.items():
        src = "/static/nophoto.png"  # FIXME
        dl = etree.SubElement(author, "dl", **{'class': k})
        etree.SubElement(dl, "dt").text = "Photo"
        dd = etree.SubElement(dl, "dd")
        etree.SubElement(dd, "img", height=v, width=v, src=src,
                         **{'class': "photo avatar"})

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
    if guid == 'public':
        assert(False)

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

    return 'OK'


@blueprint.route('/people/<string:guid>', methods=['GET'])
def json_feed(guid):
    """
    Look up the User identified by GUID and return the User's public feed
    in the requested format (eg. "atom", "json").
    """
    # FIXME - stub implementation
    return json.dumps([])


@blueprint.route('/diaspora/run_queue', methods=['GET'])
@require_logged_in_user
def run_queue(_user):
    process_incoming_queue(_user)
    return 'OK'


@blueprint.route('/diaspora/contacts/<string:addr>', methods=['GET'])
@require_logged_in_user
def external_contact(addr, _user):
    diasp = DiasporaContact.get_by_username(addr)
    if not diasp:
        abort(404, 'Could not find contact with this address')
    return redirect(url_for(
        'contacts.profile',
        contact_id=diasp.contact.id,
        _external=True
    ))
