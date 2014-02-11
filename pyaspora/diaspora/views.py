"""
Actions/display relating to Contacts. These may be locally-mastered (who
can also do User actions), but they may be Contacts on other nodes using
cached information.
"""

import base64
import json
from flask import abort, Blueprint, request, url_for
from lxml import etree

from pyaspora.contact.models import Contact
from pyaspora.diaspora.models import MessageQueue
from pyaspora.utils.rendering import send_xml

blueprint = Blueprint('diaspora', __name__, template_folder='templates')


@blueprint.route('/.well-known/host-meta')
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
        template=url_for('.webfinger', guid='') + '{uri}',
        type='application/xrd+xml'
    )
    return send_xml(doc)


@blueprint.route('/diaspora/webfinger/<string:contact_addr>')
def webfinger(contact_addr):
    """
    Returns the Webfinger profile for a contact called <contact> (in
    "user@host" form).
    """
    contact_id, _ = contact_addr.split('@')
    c = Contact.get(int(contact_id))
    if c is None or not c.user:
        abort(404, 'No such contact')

    ns = 'http://docs.oasis-open.org/ns/xri/xrd-1.0'
    doc = etree.Element("{%s}XRD" % ns, nsmap={None: ns})
    etree.SubElement(doc, "Subject").text = "acct:%s" % c.id
    etree.SubElement(doc, "Alias").text = \
        '"{0}"'.format(url_for('index', _external=True))
    etree.SubElement(
        doc, "Link",
        rel='http://microformats.org/profile/hcard',
        type='text/html',
        href=url_for('.hcard', guid=c.guid, _external=True)
    )
    etree.SubElement(
        doc, "Link",
        rel='http://joindiaspora.com/seed_location',
        type='text/html',
        href=url_for('index')
    )
    etree.SubElement(
        doc, "Link",
        rel='http://joindiaspora.com/guid',
        type='text/html',
        href=c.guid
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


@blueprint.route('/diaspora/hcard/<string:guid>')
def hcard(guid):
    """
    Returns the hCard for the User with GUID <guid>. I would have
    preferred to use the primary key, but the protocol insists on
    fetch-by-GUID.
    """
    c = Contact.get_by_guid(guid)
    if c is None or not c.user:
        abort(404, 'No such contact')

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


@blueprint.route('/receive/users/<string:guid>')
def receive(guid):
    """
    Receive a Salmon Slap and save it for when the user logs in.
    """
    c = Contact.get_by_guid(guid)
    if c is None or not c.user:
        abort(404, 'No such contact')

    queue_item = MessageQueue()
    queue_item.local = c.user
    queue_item.remote = None
    queue_item.format = MessageQueue.INCOMING
    queue_item.body = request.data
    db.session.add(queue_item)
    db.session.commit()

    return 'OK'


@blueprint.route('/people/<string:guid>')
def json_feed(guid):
    """
    Look up the User identified by GUID and return the User's public feed
    in the requested format (eg. "atom", "json").
    """
    # FIXME - stub implementation
    return json.dumps([])
