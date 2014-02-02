import base64
import cherrypy
import json

from lxml import etree

import pyaspora.model as model

from pyaspora.tools.sqlalchemy import session


class DiasporaController:
    def host_meta(self):
        """
        Return a WebFinder host-meta, which points the client to the end-point
        for webfinger querying.
        """
        ns = 'http://docs.oasis-open.org/ns/xri/xrd-1.0'
        doc = etree.Element("{%s}XRD" % ns, nsmap={None: ns})
        etree.SubElement(
            doc, "Link",
            rel='lrdd',
            template=cherrypy.request.base + '/diaspora/webfinger/{uri}',
            type='application/xrd+xml'
        )
        return self.send_xml(doc)

    @cherrypy.expose
    def webfinger(self, contact):
        """
        Returns the Webfinger profile for a contact called <contact> (in
        "user@host" form).
        """
        c = model.Contact.get_by_username(contact)

        if c is None or not c.user:
            cherrypy.response.status = 404
            return "No such contact"

        ns = 'http://docs.oasis-open.org/ns/xri/xrd-1.0'
        doc = etree.Element("{%s}XRD" % ns, nsmap={None: ns})
        etree.SubElement(doc, "Subject").text = "acct:%s" % c.username
        etree.SubElement(doc, "Alias").text = '"%s/"' % cherrypy.request.base
        etree.SubElement(
            doc, "Link",
            rel='http://microformats.org/profile/hcard',
            type='text/html',
            href=cherrypy.request.base + '/diaspora/hcard/' + str(c.user.guid)
        )
        etree.SubElement(
            doc, "Link",
            rel='http://joindiaspora.com/seed_location',
            type='text/html',
            href=cherrypy.request.base + '/'
        )
        etree.SubElement(
            doc, "Link",
            rel='http://joindiaspora.com/guid',
            type='text/html',
            href=str(c.user.guid)
        )
        etree.SubElement(
            doc, "Link",
            rel='http://schemas.google.com/g/2010#updates-from',
            type='application/atom+xml',
            href=cherrypy.request.base + '/contact/feed/' + str(c.username)  # FIXME
        )
        etree.SubElement(
            doc, "Link",
            rel='diaspora-public-key',
            type='RSA',
            href=base64.b64encode(c.public_key.encode('ascii'))
        )

        return self.send_xml(doc)

    @cherrypy.expose
    def hcard(self, guid):
        """
        Returns the hCard for the User with GUID <guid>. I would have
        preferred to use the primary key, but the protocol insists on
        fetch-by-GUID.
        """
        c = model.User.get_by_guid(guid)

        if c is None:
            cherrypy.response.status = 404
            return "No such contact"

        ns = 'http://www.w3.org/1999/xhtml'
        doc = etree.Element("{%s}div" % ns, nsmap={None: ns}, id="content")
        etree.SubElement(doc, "h1").text = c.contact.realname
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
            dd, 'a', rel='me', href=cherrypy.request.base + '/', **{
                'class': "nickname url uid"}
        ).text = c.contact.realname

        dl = etree.SubElement(author, 'dl', **{'class': "entity_fn"})
        etree.SubElement(dl, 'dt').text = 'Full name'
        dd = etree.SubElement(dl, 'dd').text = c.contact.realname

        dl = etree.SubElement(author, 'dl', **{'class': "entity_url"})
        etree.SubElement(dl, 'dt').text = 'URL'
        dd = etree.SubElement(dl, 'dd')
        etree.SubElement(dd, 'a', id='pod_location', rel='me',
                         href=cherrypy.request.base + '/',
                         **{'class': "url"}).text = cherrypy.request.base + '/'

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

        return self.send_xml(doc, content_type='text/html')

    def send_xml(self, doc, content_type='text/xml'):
        """
        Utility function to return XML to the client. This is abstracted out
        so that pretty-printing can be turned on and off in one place.
        """
        cherrypy.response.headers['Content-Type'] = content_type
        return etree.tostring(doc, xml_declaration=True, pretty_print=True, encoding="UTF-8")

    def receive(self, guid, xml):
        """
        Receive a Salmon Slap and save it for when the user logs in.
        """
        u = model.User.get_by_guid(guid)
        if u is None:
            cherrypy.response.status = 404
            return "No such contact"

        queue_item = model.MessageQueue()
        queue_item.local = u
        queue_item.remote = None
        queue_item.format = model.MessageQueue.INCOMING
        queue_item.body = xml
        session.add(queue_item)
        session.commit()

        return 'OK'

        #m = DiasporaMessageParser(model)
        #print(m.decode(xml, model.User.get_by_guid(guid), 'test'))
        #return xml

    def json_feed(self, guid):
        """
        Look up the User identified by GUID and return the User's public feed
        in the requested format (eg. "atom", "json").
        """
        # FIXME - stub implementation
        return json.dumps([])

    @classmethod
    def import_contact(cls, uri, contact):
        """
        Fetch information about a Diaspora user and import it into the Contact provided.
        """
        WEBFINGER_NS = "http://docs.oasis-open.org/ns/xri/xrd-1.0"
        w = WebfingerRequest(uri)
        webfinger = w.fetch()
        hcard_url = webfinger.find(".//{%s}Link[@rel='http://microformats.org/profile/hcard']" % WEBFINGER_NS).get("href")
        hcard = etree.parse(urllib.request.urlopen(hcard_url), etree.HTMLParser())
        contact.username = uri
        contact.realname = hcard.find(".//span[@class='fn']").text
        contact.engine = "diaspora"
        contact.engine_info = json.dumps({
            "guid": webfinger.find(".//{%s}Link[@rel='http://joindiaspora.com/guid']" % WEBFINGER_NS).get("href"),
            "server": webfinger.find(".//{%s}Link[@rel='http://joindiaspora.com/seed_location']" % WEBFINGER_NS).get("href")
        })
        contact.public_key = base64.b64decode(
            webfinger.find(".//{%s}Link[@rel='diaspora-public-key']" % WEBFINGER_NS)
            .get("href").encode("ascii"))

    def subscribe(self, user, group='All', subtype='friend'):
        """
        Local User <user> would like to subscribe to the Contact represented
        by this transport. The Subscription object will be returned. The
        Subscription will be of subscription type <subtype> (eg. "friend",
        "feed"), and will be added to the User's SubscriptionGroup named by
        <group>.
        """
        req = etree.Element("request")
        etree.SubElement(req, "sender_handle").text = user.contact.username
        etree.SubElement(req, "recipient_handle").text = \
            self.contact().username
        m = DiasporaMessageBuilder(req, user)
        url = self.get_server() + "receive/users/" + self.get_guid()
        print("Sending message to " + url)
        m.post(url, self.contact(), 'test')  # FIXME
        Transport.refresh_feeds(self, contact=self.contact())

"""
Diaspora hard-codes a variety of URLs. This Dispatcher traps them and maps them
to URLs on the DiasporaController.
"""
diaspora_dispatcher = cherrypy.dispatch.RoutesDispatcher()
diaspora_dispatcher.connect('well_known', '/.well-known/host-meta',
                            DiasporaController(), action='host_meta')
diaspora_dispatcher.connect('receive', '/receive/users/:guid',
                            DiasporaController(), action='receive')
diaspora_dispatcher.connect('receive', '/people/:guid',
                            DiasporaController(), action='json_feed')

class Test:
    @cherrypy.expose
    def queue(self):
        u = User.logged_in()
        k = User.get_user_key()
        assert(k)
        import pyaspora.diaspora
        dmp = pyaspora.diaspora.DiasporaMessageParser(model)
        op = '<html><body><table>'
        import cgi
        for msg in u.message_queue:
            op += '<tr><th>raw</th><td>{}</td></tr>'.format(msg.body.decode('utf-8'))
            try:
                op += '<tr><th>parsed</th><td>{}</td></tr>'.format(cgi.escape(repr(dmp.decode(msg.body.decode('utf-8'), k))))
            except Exception:
                import traceback
                op += '<tr><th>error</th><td>{}</td></tr>'.format(traceback.format_exc())
        op += '</table></body></html>'
        return op

#     @cherrypy.expose
#     def test(self):
#         """
#         temporary test of round-tripping the message builder and parser
#         """
#         #u = model.User.get(1)
#         #m = DiasporaMessageBuilder('Hello, world!', u)
#         #print(m.post('http://localhost:8080/receive/users/'+u.guid, u.contact, 'test'))
#         #return "OK"
#         #c = pyaspora.transport.diaspora.Transport.import_contact("lukeross@diasp.eu")
#         #session.add(c)
#         u = model.User.get(1)
#         c = model.Contact.get_by_username("lukeross@diasp.eu")
#         c.subscribe(u, "friend")
#         return "OK"
