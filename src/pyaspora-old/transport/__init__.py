import base64
import json
import urllib.request
import weakref

from lxml import etree

import pyaspora.model

from pyaspora.transport.diaspora import DiasporaMessageBuilder, WebfingerRequest

class Transport:
    """
    Abstract class that handles the protocol that communicates with a Contact.
    """
    def __init__(self, contact):
        """
        Create a new Transport object for one Contact <contact>
        """
        self.contact = weakref.ref(contact)
        
    def share(self, post, privacy):
        """
        Share Post <post> with the Transport's contact. Returns the Share object that
        represents the sharing of the Post with the contact. The Share will be created
        with a PrivacyLevel of <privacy> 
        """
        pass
    
    def subscribe(self, user, group='All', subtype='friend'):
        """
        Local User <user> would like to subscribe to the Contact represented by this
        transport. The Subscription object will be returned. The Subscription will be
        of subscription type <subtype> (eg. "friend", "feed"), and will be added to the
        User's SubscriptionGroup named by <group>.
        """
        self.refresh_feeds(contact = self.contact())
    
    def refresh_feeds(self, contact=None):
        """
        Update this contact's "wall"/"public feed". If <contact> is not supplied, the
        whole contact feed will be refreshed. Otherwise only posts between the Transport
        contact and contact <contact> will be refreshed. Transports may choose to ignore
        <contact>.
        """
        pass
    
    @classmethod
    def import_contact(cls, username):
        """
        On a given Transport class, fetch user with username <username> from the remote
        server and create a corresponding Contact in the local database, returning the
        newly-created Contact.
        """
        pass
    
    def guid(self, contact):
        """
        Return the globally unique ID ("GUID") for this Contact (a string).
        """
        return contact.user.guid
    
    def public_key(self, contact):
        """
        Return the public key for this Contact (a string containing a PEM-encoded
        public key.
        """
        return contact.public_key

class Local(Transport):
    """
    The Transport for a local user - a user who is mastered on this server, who logs in here
    and for whom authoratative information is stored in the local database.
    """
    def __init__(self, contact):
        """
        Create a Transport object for a User who is mastered on the local server - i.e.
        one who logs in here.
        """
        return Transport.__init__(self, contact)
    
    def subscribe(self, user, group='All', subtype='friend'):
        """
        Subscribe a local User <user> to a local Contact. This is purely a database operation
        with no network operation.
        """
        Transport.subscribe(self, user, group, subtype)
        # Share everything I authored with this new person
        for share in self.contact().posts:
            if share.post.has_permission_to_view(user.contact):
                share.post.share_with([ user.contact ], share.post.privacy_level)
                
class Diaspora(Transport):
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
        contact.public_key = base64.b64decode(webfinger.find(".//{%s}Link[@rel='diaspora-public-key']" % WEBFINGER_NS).get("href").encode("ascii"))
    
    def subscribe(self, user, group='All', subtype='friend'):
        """
        Local User <user> would like to subscribe to the Contact represented by this
        transport. The Subscription object will be returned. The Subscription will be
        of subscription type <subtype> (eg. "friend", "feed"), and will be added to the
        User's SubscriptionGroup named by <group>.
        """
        req = etree.Element("request")
        etree.SubElement(req, "sender_handle").text = user.contact.username
        etree.SubElement(req, "recipient_handle").text = self.contact().username
        m = DiasporaMessageBuilder(req, user)
        url = self.get_server() + "receive/users/" + self.get_guid()
        print("Sending message to " + url)
        m.post(url, self.contact(), 'test') # FIXME
        Transport.refresh_feeds(self, contact=self.contact())
        
    def get_server(self):
        info = json.loads(self.contact().engine_info)
        return info["server"]
    
    def get_guid(self):
        info = json.loads(self.contact().engine_info)
        return info["guid"]