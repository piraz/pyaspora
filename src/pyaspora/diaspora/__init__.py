import base64
import cherrypy
import cherrypy._cpdispatch
import Crypto.Random
import json
import re
import urllib
import urllib.parse
import urllib.request
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5 as PKCSSign

from lxml import etree, html

from pyaspora import model

# This package contains Diaspora-protocol-specific code.

PROTOCOL_NS="https://joindiaspora.com/protocol" # The namespace for the Diaspora envelope
    
class DiasporaMessageBuilder:
    """
    A class to take a payload message and wrap it in the outer Diaspora message format,
    including building the envelope and performing the encryption.
    
    Much of the terminology in the method names comes directly from the protocol documentation
    at https://github.com/diaspora/diaspora/wiki/Federation-Protocol-Overview
    """
    def __init__(self, message, author):
        """
        Build a Diaspora message and prepare to send the payload <message>, authored by Contact
        <author>. The receipient is specified later, so that the same message can be sent to several
        people without needing to keep re-encrypting the inner.
        """
        
        # We need an AES key for the envelope
        self.inner_iv = Crypto.Random.get_random_bytes(AES.block_size)
        self.inner_key = Crypto.Random.get_random_bytes(32)
        self.inner_encrypter = AES.new(self.inner_key, AES.MODE_CBC, self.inner_iv)
        
        # ...and one for the payload message
        self.outer_iv = Crypto.Random.get_random_bytes(AES.block_size)
        self.outer_key = Crypto.Random.get_random_bytes(32)
        self.outer_encrypter = AES.new(self.outer_key, AES.MODE_CBC, self.outer_iv)
        self.message = message
        self.author = author
    
    def xml_to_string(self, doc, xml_declaration=False):
        """
        Utility function to turn an XML document to a string. This is abstracted out so that
        pretty-printing can be turned on and off in one place.
        """
        return etree.tostring(doc, xml_declaration=xml_declaration, pretty_print=True, encoding="UTF-8")
    
    def create_decrypted_header(self):
        """
        Build the XML document for the header. The header contains the key used to encrypt the
        message body.
        """
        decrypted_header = etree.Element("decrypted_header")
        etree.SubElement(decrypted_header, "iv").text = base64.b64encode(self.inner_iv)
        etree.SubElement(decrypted_header, "aes_key").text = base64.b64encode(self.inner_key)
        etree.SubElement(decrypted_header, "author_id").text = self.author.contact.username
        return self.xml_to_string(decrypted_header)
    
    def create_ciphertext(self):
        """
        Encrypt the header.
        """
        to_encrypt = self.pkcs7_pad(self.create_decrypted_header(), AES.block_size)
        out = self.outer_encrypter.encrypt(to_encrypt)
        return out
    
    def create_outer_aes_key_bundle(self):
        """
        Record the information on the key used to encrypt the header.
        """
        d = json.dumps({
            "iv": base64.b64encode(self.outer_iv).decode("ascii"),
            "key": base64.b64encode(self.outer_key).decode("ascii")
        })
        return d
        
    def create_encrypted_outer_aes_key_bundle(self, recipient):
        """
        The Outer AES Key Bundle is encrypted with the receipient's public key, so
        only the receipient can decrypt the header.
        """
        recipient_rsa = RSA.importKey(recipient.public_key)
        cipher = PKCS1_v1_5.new(recipient_rsa)
        return cipher.encrypt(self.create_outer_aes_key_bundle().encode("utf-8"))
    
    def create_encrypted_header_json_object(self, recipient):
        """
        The actual header and the encrypted outer (header) key are put into a document together.
        """
        d = json.dumps({
            "aes_key": base64.b64encode(self.create_encrypted_outer_aes_key_bundle(recipient)).decode("ascii"),
            "ciphertext": base64.b64encode(self.create_ciphertext()).decode("ascii")
        })
        return d
    
    def create_encrypted_header(self, recipient):
        """
        The "encrypted header JSON object" is dropped into some XML. I am not sure what this
        is for, but is required to interact.
        """
        doc = etree.Element("encrypted_header")
        doc.text = base64.b64encode(self.create_encrypted_header_json_object(recipient).encode("ascii"))
        return doc
    
    def create_payload(self):
        """
        Wrap the actual payload message in the standard XML wrapping.
        """
        doc = etree.Element("XML")
        inner = etree.SubElement(doc, "post")
        if isinstance(self.message, str):
            inner.text = self.message
        else:
            inner.append(self.message)
        print("payload=" + repr(self.xml_to_string(doc)))
        return self.xml_to_string(doc)
    
    def create_encrypted_payload(self):
        """
        Encrypt the payload XML with the inner (body) key.
        """
        to_encrypt = self.pkcs7_pad(self.create_payload(), AES.block_size)
        return self.inner_encrypter.encrypt(to_encrypt)
        
    def create_salmon_envelope(self, recipient, password):
        """
        Build the whole message, pulling together the encrypted payload and the
        encrypted header. Selected elements are signed by the author so that tampering
        can be detected.
        """
        nsmap = {
            None: PROTOCOL_NS,
            'me': 'http://salmon-protocol.org/ns/magic-env'
        }
        doc = etree.Element("{%s}diaspora" % nsmap[None], nsmap=nsmap)
        doc.append(self.create_encrypted_header(recipient))      
        env = etree.SubElement(doc, "{%s}env" % nsmap["me"])
        etree.SubElement(env, "{%s}encoding" % nsmap["me"]).text = 'base64url'
        etree.SubElement(env, "{%s}alg" % nsmap["me"]).text = 'RSA-SHA256'
        payload = base64.urlsafe_b64encode(base64.b64encode(self.create_encrypted_payload())).decode("ascii")
        # Split every 6 chars
        payload = '\n'.join([payload[start:start+60] for start in range(0, len(payload), 60)])
        payload = payload + "\n"
        etree.SubElement(env, "{%s}data" % nsmap["me"], {"type":"application/xml"}).text = payload
        sig_contents = payload + "." + base64.b64encode(b"application/xml").decode("ascii") + "." + \
            base64.b64encode(b"base64url").decode("ascii") + "." + base64.b64encode(b"RSA-SHA256").decode("ascii")
        print("sig_contents=" + repr(sig_contents))
        sig_hash = SHA256.new(sig_contents.encode("ascii"))
        author_rsa = RSA.importKey(self.author.private_key, password)
        cipher = PKCSSign.new(author_rsa)
        sig = base64.urlsafe_b64encode(cipher.sign(sig_hash))
        etree.SubElement(env, "{%s}sig" % nsmap["me"]).text = sig
        print(self.xml_to_string(doc))
        return self.xml_to_string(doc)
    
    def pkcs7_pad(self, inp, block_size):
        """
        Using the PKCS#7 padding scheme, pad <inp> to be a multiple of <block_size> bytes. Ruby's
        AES encryption pads with this scheme, but pycrypto doesn't support it.
        """
        val = block_size - len(inp) % block_size
        if val == 0:
            return inp + (bytes([block_size]) * block_size)
        else:
            return inp + (bytes([val]) * val)

    def post(self, url, recipient, password):
        """
        Actually send the message to an HTTP/HTTPs endpoint.
        """
        data = urllib.parse.urlencode({'xml': urllib.parse.quote(self.create_salmon_envelope(recipient, password))})
        return urllib.request.urlopen(url, data.encode("ascii"))
    
class DiasporaMessageParser:
    """
    After CherryPy has received a Salmon Slap, this decodes it to extract the payload,
    validating the signature.
    """
    
    def __init__(self, model):
        self.model = model
            
    def decode(self, raw, key):
        """
        Extract the envelope XML from its wrapping.
        """
        # It has already been URL-decoded once by cherrypy
        xml = urllib.parse.unquote_plus(raw)
        return self.process_salmon_envelope(xml, key)
    
    def process_salmon_envelope(self, xml, key):
        """
        Given the Slap XML, extract out the author and payload.
        """
        xml = xml.lstrip().encode("utf-8")
        #print("salmon_envelope=" + repr(xml))
        doc = etree.fromstring(xml)
        header = self.parse_header(doc.find(".//{"+PROTOCOL_NS+"}encrypted_header").text, key)
        sender = header.find(".//author_id").text
        inner_iv = base64.b64decode(header.find(".//iv").text.encode("ascii"))
        inner_key = base64.b64decode(header.find(".//aes_key").text.encode("ascii"))
        
        sending_contact = self.model.Contact.get_by_username(sender)
        if sending_contact is None:
            sending_contact = import_contact(sender)
        self.verify_signature(sending_contact, doc)
        
        decrypter = AES.new(inner_key, AES.MODE_CBC, inner_iv)
        body = doc.find(".//{http://salmon-protocol.org/ns/magic-env}data").text
        body = base64.b64decode(base64.urlsafe_b64decode(body.encode("ascii")))
        body = decrypter.decrypt(body)
        body = self.pkcs7_unpad(body)
        return body
    
    def verify_signature(self, user, message):
        """
        Verify the signed XML elements to have confidence that the claimed author
        did actually generate this message.
        """
        pass # FIXME
    
    def parse_header(self, b64data, key):
        """
        Extract the header and decrypt it. This requires the User's private key and hence
        the passphrase for the key.
        """
        decoded_json = base64.b64decode(b64data.encode("ascii"))
        rep = json.loads(decoded_json.decode("ascii"))
        outer_key_details = self.decrypt_outer_aes_key_bundle(rep["aes_key"], key)
        header = self.get_decrypted_header(base64.b64decode(rep["ciphertext"].encode("ascii")),
            key=base64.b64decode(outer_key_details["key"].encode("ascii")), 
            iv=base64.b64decode(outer_key_details["iv"].encode("ascii")))
        return header

    def decrypt_outer_aes_key_bundle(self, data, key):
        """
        Decrypt the AES "outer key" credentials using the private key and passphrase.
        """
        assert(key)
        cipher = PKCS1_v1_5.new(key)
        decoded_json = cipher.decrypt(base64.b64decode(data.encode("ascii")), sentinel=None)
        return json.loads(decoded_json.decode("ascii"))
    
    def get_decrypted_header(self, ciphertext, key, iv):
        """
        Having extracted the AES "outer key" (envelope) information, actually decrypt the header.
        """
        encrypter = AES.new(key, AES.MODE_CBC, iv)
        padded = encrypter.decrypt(ciphertext)
        xml = self.pkcs7_unpad(padded)
        doc = etree.fromstring(xml)
        return doc

    def pkcs7_unpad(self, data):
        """
        Remove the padding bytes that were added at point of encryption.
        """
        return data[0:-data[-1]]

class WebfingerRequest(object):
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
        print("in wf fetch")
        template_url = self._get_template()
        target_url = re.sub('\{uri\}', urllib.parse.quote_plus(self.request_email.scheme + ':' + self.request_email.path), template_url)
        print("about to connect to {}".format(target_url))
        return etree.parse(urllib.request.urlopen(target_url))
    
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
        print("hostmeta connection to {}".format(url))
        request = urllib.request.Request(url)
        opener = urllib.request.build_opener(RedirectTrackingHandler())
        return opener.open(request, timeout=5)
    
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
        
def import_contact(addr):
    print("in import_contact")
    try:
        wf = WebfingerRequest(addr).fetch()
    except urllib.error.URLError:
        return None
    print("wf returned {}".format(repr(wf)))
    if not wf:
        return None
    
    NS = {'XRD': 'http://docs.oasis-open.org/ns/xri/xrd-1.0'}
    
    c = model.Contact()
    c.username = wf.xpath('//XRD:Subject/text()', namespaces=NS)[0].split(':')[1]
    pk = wf.xpath('//XRD:Link[@rel="diaspora-public-key"]/@href', namespaces=NS)[0]
    c.public_key = base64.b64decode(pk).decode("ascii")
    hcard_url = wf.xpath('//XRD:Link[@rel="http://microformats.org/profile/hcard"]/@href', namespaces=NS)[0]
    
    hcard = html.parse(urllib.request.urlopen(hcard_url))
    print(etree.tostring(hcard, pretty_print=True))
    c.realname = hcard.xpath('//*[@class="fn"]')[0].text
    
    photo_url = hcard.xpath('//*[@class="entity_photo"]//img/@src')
    if photo_url:
        resp = urllib.request.urlopen(urllib.parse.urljoin(hcard_url, photo_url[0]))
        mp = model.MimePart()
        mp.type = resp.info().get('Content-Type')
        mp.body = resp.read()
        mp.text_preview = '(picture for {})'.format(c.realname)
        c.avatar = mp
    
    return c

class DiasporaMessageProcessor:
    @classmethod
    def process(cls, message):
        xml = xml.lstrip().encode("utf-8")
        doc = etree.fromstring(xml)
        for xpath, handler in cls.TYPES:
            if doc.xpath(xpath):
                return handler(cls, doc)

    @classmethod
    def subscription_request(cls, doc):
        pass

    @classmethod
    def profile_receive(cls, doc):
        pass

    TYPES = {
        '/diaspora/post/receive', subscription_request,
        '/diaspora/post/profile', profile_receive,
    }
