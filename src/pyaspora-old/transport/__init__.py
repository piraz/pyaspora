import base64
import json
import urllib.request
import weakref

from lxml import etree

import pyaspora.model

from pyaspora.transport.diaspora import DiasporaMessageBuilder, WebfingerRequest

class Local(Transport):
    """
    The Transport for a local user - a user who is mastered on this server, who logs in here
    and for whom authoratative information is stored in the local database.
    """
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
        #    "server": webfinger.find(".//{%s}Link[@rel='http://joindiaspora.com/seed_location']" % WEBFINGER_NS).get("href")
    
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
