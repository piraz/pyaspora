import base64
import urllib.error
import urllib.parse
import urllib.request
from lxml import etree, html

from pyaspora.contact.models import Contact
from pyaspora.content.models import MimePart
from pyaspora.database import db
from pyaspora.diaspora.models import DiasporaContact, MessageQueue
from pyaspora.diaspora.protocol import DiasporaMessageBuilder, WebfingerRequest


def process_incoming_queue(user, rsa_key):
    messages = db.session.query(MessageQueue).filter(
        and_(
            MessageQueue.format == MessageQueue.INCOMING,
            MessageQueue.user_id == user.id
        )
    )
    for message in messages:
        # FIXME
        m = DiasporaMessageParser(model)
        print(m.decode(xml, rsa_key))


def subscribe(user, contact, private_key, password):
    """
    Local User <user> would like to subscribe to the Contact represented by
    this transport. The Subscription object will be returned. The Subscription
    will be of subscription type <subtype> (eg. "friend", "feed"), and will be
    added to the User's SubscriptionGroup named by <group>.
    """
    req = etree.Element("request")
    etree.SubElement(req, "sender_handle").text = str(user.contact.id)
    etree.SubElement(req, "recipient_handle").text = contact.diasp.username
    m = DiasporaMessageBuilder(req, user)
    url = "http://{0}/receive/users/{1}".format(
        contact.diasp.server, contact.diasp.guid)
    m.post(url, contact, password)


def import_contact(addr):
    """
    Fetch information about a Diaspora user and import it into the Contact
    provided.
    """
    try:
        wf = WebfingerRequest(addr).fetch()
    except urllib.error.URLError:
        return None
    if not wf:
        return None

    NS = {'XRD': 'http://docs.oasis-open.org/ns/xri/xrd-1.0'}

    c = Contact()

    pk = wf.xpath('//XRD:Link[@rel="diaspora-public-key"]/@href',
                  namespaces=NS)[0]
    c.public_key = base64.b64decode(pk).decode("ascii")

    hcard_url = wf.xpath(
        '//XRD:Link[@rel="http://microformats.org/profile/hcard"]/@href',
        namespaces=NS
    )[0]
    hcard = html.parse(urllib.request.urlopen(hcard_url))
    print(etree.tostring(hcard, pretty_print=True))
    c.realname = hcard.xpath('//*[@class="fn"]')[0].text

    photo_url = hcard.xpath('//*[@class="entity_photo"]//img/@src')
    if photo_url:
        resp = urllib.request.urlopen(
            urllib.parse.urljoin(hcard_url, photo_url[0])
        )
        mp = MimePart()
        mp.type = resp.info().get('Content-Type')
        mp.body = resp.read()
        mp.text_preview = '(picture for {})'.format(c.realname)
        c.avatar = mp

    username = wf.xpath('//XRD:Subject/text()', namespaces=NS)[0].split(':')[1]
    guid = wf.xpath(
        ".//Link[@rel='http://joindiaspora.com/guid']",
        namespaces=NS
    ).get("href"),
    server = wf.xpath(
        ".//Link[@rel='http://joindiaspora.com/seed_location']",
        namespaces=NS
    ).get("href")
    d = DiasporaContact(
        contact=c,
        guid=guid,
        username=username,
        server=server
    )
    db.session.add(d)
    db.session.add(c)

    return c
