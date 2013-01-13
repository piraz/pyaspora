# Classes for making a WebFinger request against a remote server

from lxml import etree
import re
import urllib.parse
import urllib.request

class Request(object):
    '''
    A request for WebFinder information for a particular Diaspora user. 
    '''

    def __init__(self, email):
        '''
        Create a request for information to Diaspora user with username <email> (of form
        "user@host".
        '''
        self.request_email = email
        self.secure = True
        self.normalise_email();
        
    def fetch(self):
        """
        Fetch the WebFinger profile and return the XML document.
        """
        template_url = self._get_template()
        target_url = re.sub('\{uri\}', urllib.parse.quote_plus(self.request_email.scheme + ':' + self.request_email.path), template_url)
        request = urllib.request.Request(target_url)
        opener = urllib.request.build_opener(RedirectTrackingHandler())
        return etree.parse(opener.open(request))
    
    def _get_template(self):
        """
        Given the HostMeta, extract the template URL for the main WebFinger information.
        """
        tree = self.hostmeta.fetch()
        return (tree.xpath("//x:Link[@rel='lrdd']/@template", namespaces={'x': 'http://docs.oasis-open.org/ns/xri/xrd-1.0'}))[0]
    
    def normalise_email(self):
        """
        Normalise the email address provides into an account URL
        """
        url = urllib.parse.urlparse(self.request_email, "acct")
        if url.scheme != "acct":
            raise TypeError()
        self.request_email = url
        match = re.match('.*\@(.*)', url.path)
        self.hostmeta = HostMeta(match.group(1))

class HostMeta(object):
    '''
    A request for a HostMeta on a remote server.
    '''

    def __init__(self, hostname):
        '''
        Create a fetch request for host name <hostname>.
        '''
        self.request_host = hostname
        self.secure = True
        
    def _build_url(self, scheme):
        """
        Create the URL to fetch on the remote host.
        """
        return scheme + "://" + self.request_host + "/.well-known/host-meta"

    def _open_url(self, url):
        """
        Create the connection to the remote host.
        """
        request = urllib.request.Request(url)
        opener = urllib.request.build_opener(RedirectTrackingHandler())
        return opener.open(request)
    
    def _get_connection(self):
        """
        Try to connect to the remote host, using HTTPS and falling back to HTTP. Track
        whether any steps in fetching it (redirects) are insecure.
        """
        try:
            res = self._open_url(self._build_url("https"))
        except:
            self.secure = False
            res = self._open_url(self._build_url("http"))

        if self.secure and hasattr(res, "redirected_via"):
            # Check redirections
            for u in res.redirected_via:
                up = urllib.parse.urlparse(u)
                if up.scheme != "https":
                    self.secure = False
                    break
        
        return res
            
    def fetch(self):
        """
        Fetch and return the HostMeta XML document.
        """
        conn = self._get_connection()
        tree = etree.parse(conn)
        if not self.secure:
            self.validate_signature(tree)
                                    
        return tree

    def validate_signature(self, tree):
        """
        If any part of fetching the HostMeta occurs insecurely (eg. over HTTP)
        then attempt to fetch and validate the signature of the HostMeta).
        """
        return True # FIXME - implement
        print(etree.tostring(tree))
            
class RedirectTrackingHandler(urllib.request.HTTPRedirectHandler):
    """
    Utility class that spots if we are redirected via a non-HTTPS site.
    """
    def http_error_301(self, req, fp, code, msg, headers):
        new_url = req.get_full_url()
        print(repr(headers))
        result = urllib.request.HTTPRedirectHandler.http_error_301(self, req, fp, code, msg, headers)
        if not hasattr(result, "redirected_via"):
            result.redirected_via = []
        result.redirected_via.append(new_url)

    def http_error_302(self, req, fp, code, msg, headers):
        previous_url = req.url        
        result = urllib.request.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
        if not hasattr(result, "redirected_via"):
            result.redirected_via = []
        result.redirected_via.append(previous_url)