import base64
import cherrypy
import json
import re

from lxml import etree

import pyaspora.model as model

from pyaspora.transport.diaspora import DiasporaMessageParser

class DiasporaDispatcher(cherrypy._cpdispatch.Dispatcher):
    """
    Diaspora hard-codes a variety of URLs. This Dispatcher traps them and maps them to
    URLs on the DiasporaController.
    
    FIXME: This should perhaps be replaced with CherryPy's Rails Dispatcher so they are explicit,
    but I rather like the CherryPy dispatcher and don't want to universally override it. I think
    this can be done with CherryPy's configuration system, but this needs to be checked out.
    """
    def find_handler(self, path):
        """
        Given a string request path <path>, trap and re-map it if it's a Diaspora-specific URL,
        otherwise do the default action.
        """
        
        # Webfinger
        if path=="/.well-known/host-meta":
            return cherrypy._cpdispatch.Dispatcher.find_handler(self, '/diaspora/host_meta')
        
        # Salmon end-point
        res = re.match('/receive/users/(.*)', path)
        if res:
            return cherrypy._cpdispatch.Dispatcher.find_handler(self, '/diaspora/receive/' + res.group(1))
        
        # JSON representation of the user public feed
        res = re.match('/people/(.*)', path)
        if res:
            return cherrypy._cpdispatch.Dispatcher.find_handler(self, '/diaspora/feed/' + res.group(1) + '/json')        
        
        # None of the above
        return cherrypy._cpdispatch.Dispatcher.find_handler(self, path)

class DiasporaController:  
    @cherrypy.expose
    def host_meta(self):
        """
        Return a WebFinder host-meta, which points the client to the end-point for
        webfinger querying.
        """
        ns = 'http://docs.oasis-open.org/ns/xri/xrd-1.0'
        doc = etree.Element("{%s}XRD" % ns, nsmap={None: ns})
        etree.SubElement(doc, "Link",
            rel='lrdd',
            template=cherrypy.request.base + '/diaspora/webfinger/{uri}',
            type = 'application/xrd+xml'
        )
        return self.send_xml(doc)
    
    @cherrypy.expose
    def webfinger(self, contact):
        """
        Returns the Webfinger profile for a contact called <contact> (in "user@host" form).
        """
        c = model.Contact.get_by_username(contact)
        
        if c is None or not c.user:
            cherrypy.response.status = 404
            return "No such contact"
        
        ns = 'http://docs.oasis-open.org/ns/xri/xrd-1.0'
        doc = etree.Element("{%s}XRD" % ns, nsmap={None: ns})
        etree.SubElement(doc, "Subject").text = "acct:%s" % c.username
        etree.SubElement(doc, "Alias").text = '"%s/"' % cherrypy.request.base
        etree.SubElement(doc, "Link", 
            rel='http://microformats.org/profile/hcard',
            type='text/html',
            href=cherrypy.request.base + '/diaspora/hcard/' + str(c.transport().guid(c))
        )
        etree.SubElement(doc, "Link", 
            rel='http://joindiaspora.com/seed_location',
            type='text/html',
            href=cherrypy.request.base + '/'
        )
        etree.SubElement(doc, "Link", 
            rel='http://joindiaspora.com/guid',
            type='text/html',
            href=str(c.transport().guid(c))
        )
        etree.SubElement(doc, "Link", 
            rel='http://schemas.google.com/g/2010#updates-from',
            type='application/atom+xml',
            href=cherrypy.request.base + '/contact/feed/' + str(c.username) # FIXME
        )        
        etree.SubElement(doc, "Link", 
            rel='diaspora-public-key',
            type='RSA',
            href=base64.b64encode(c.transport().public_key(c).encode('ascii'))
        )                
        
        return self.send_xml(doc)

    @cherrypy.expose    
    def hcard(self, guid):
        """
        Returns the hCard for the User with GUID <guid>. I would have preferred to
        use the primary key, but the protocol insists on fetch-by-GUID.
        """
        c = model.User.get_by_guid(guid)
        
        if c is None:
            cherrypy.response.status = 404
            return "No such contact"

        ns = 'http://www.w3.org/1999/xhtml'
        doc = etree.Element("{%s}div" % ns, nsmap={None: ns}, id="content")      
        etree.SubElement(doc, "h1").text = c.contact.realname
        content_inner = etree.SubElement(doc, 'div', **{'class': "content_inner"})
        author = etree.SubElement(content_inner, 'div', id="i", **{'class': "entity_profile vcard author"})
        
        etree.SubElement(author, "h2").text = "User profile"
        
        dl = etree.SubElement(author, 'dl', **{'class': "entity_nickname"})
        etree.SubElement(dl, 'dt').text = 'Nickname'
        dd = etree.SubElement(dl, 'dd')
        etree.SubElement(dd, 'a', rel='me', href=cherrypy.request.base+'/', **{'class': "nickname url uid"}).text = c.contact.realname

        dl = etree.SubElement(author, 'dl', **{'class': "entity_fn"})
        etree.SubElement(dl, 'dt').text = 'Full name'
        dd = etree.SubElement(dl, 'dd').text = c.contact.realname

        dl = etree.SubElement(author, 'dl', **{'class': "entity_url"})
        etree.SubElement(dl, 'dt').text = 'URL'
        dd = etree.SubElement(dl, 'dd')
        etree.SubElement(dd, 'a', id='pod_location', rel='me', href=cherrypy.request.base+'/', **{'class': "url"}).text = cherrypy.request.base+'/' 

        # FIXME - need to resize photos. Having no photos causes Diaspora to crash, so we
        # need to return *something* in all cases.
        photos = {
            "entity_photo": "300px",
            "entity_photo_medium": "100px",
            "entity_photo_small": "50px"
        }
        for k, v in photos.items():
            src = "/static/nophoto.png" # FIXME
            dl = etree.SubElement(author, "dl", **{'class': k})
            etree.SubElement(dl, "dt").text = "Photo"
            dd = etree.SubElement(dl, "dd")
            etree.SubElement(dd, "img", height=v, width=v, src=src, **{'class': "photo avatar"})

        dl = etree.SubElement(author, 'dl', **{'class': "entity_searchable"})
        etree.SubElement(dl, 'dt').text = 'Searchable'
        dd = etree.SubElement(dl, 'dd')
        etree.SubElement(dd, 'a', **{'class': "searchable"}).text = 'true' 
        
        return self.send_xml(doc, content_type='text/html')                
    
    def send_xml(self, doc, content_type='text/xml'):
        """
        Utility function to return XML to the client. This is abstracted out so that pretty-
        printing can be turned on and off in one place.
        """
        cherrypy.response.headers['Content-Type'] = content_type
        return etree.tostring(doc, xml_declaration=True, pretty_print=True, encoding="UTF-8")
    
    @cherrypy.expose
    def receive(self, guid, xml):
        """
        Receive a Salmon Slap and handle it.
        """
        m = DiasporaMessageParser(model)
        print(m.decode(xml, model.User.get_by_guid(guid), 'test'))
        return xml
    
    @cherrypy.expose
    def feed(self, guid, form='atom'):
        """
        Look up the User identified by GUID and return the User's public feed in
        the requested format (eg. "atom", "json").
        """ 
        # FIXME - stub implementation
        if form=='json':
            return json.dumps([])
        return "Cannot handle format"