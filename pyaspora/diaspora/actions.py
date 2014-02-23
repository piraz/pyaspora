from lxml import etree

from pyaspora.diaspora.protocol import DiasporaMessageBuilder, \
    DiasporaMessageParser
from pyaspora.diaspora.utils import addr_for_user

HANDLERS = {}


def diaspora_message_handler(xpath):
    def _inner(cls):
        HANDLERS[xpath] = cls
        return cls
    return _inner


def process_incoming_message(payload, c_from, u_to):
    xml = payload.lstrip()
    print(xml)
    doc = etree.fromstring(xml)
    for xpath, handler in HANDLERS.items():
        if doc.xpath(xpath):
            return handler.receive(doc, c_from, u_to)
    raise Exception("No handler registered", payload)


class MessageHandlerBase:
    @classmethod
    def send(cls, u_from, c_to):
        u_addr = addr_for_user(u_from)
        xml = cls.generate(u_from, c_to)
        m = DiasporaMessageBuilder(xml, u_addr, u_from._unlocked_key)
        url = "http://{0}/receive/users/{1}".format(
            c_to.diasp.server, c_to.diasp.guid)
        m.post(url, c_to.public_key)


@diaspora_message_handler('/XML/post/request')
class Subscribe(MessageHandlerBase):
    @classmethod
    def receive(cls, xml, c_from, u_to):
        """
        Contact c_from has subcribed to u_to
        """
        from_addr = xml.xpath('//sender_handle')[0].text
        assert(from_addr == c_from.diasp.username)
        c_from.subscribe(u_to.contact)

    @classmethod
    def generate(cls, u_from, c_to):
        u_addr = addr_for_user(u_from)
        req = etree.Element("request")
        etree.SubElement(req, "sender_handle").text = u_addr
        etree.SubElement(req, "recipient_handle").text = c_to.diasp.username
        return req


@diaspora_message_handler('/XML/post/profile')
class Profile(MessageHandlerBase):
    # <XML>\n          <post><profile>\n  <diaspora_handle>luke@diaspora-devel.lukeross.name</diaspora_handle>\n  
    # <first_name>fn</first_name>\n  <last_name/>\n  <image_url>/assets/user/default.png</image_url>\n 
    # <gender/>\n  <bio/>\n  <location/>\n  <searchable>false</searchable>\n  
    # <nsfw>false</nsfw>\n  <tag_string>#programming </tag_string>\n</profile></post>\n          </XML>
    
    # <XML>\n          <post><profile>\n  <diaspora_handle>luke@diaspora-devel.lukeross.name</diaspora_handle>\n
    # <first_name>fn</first_name>\n  <last_name>ln</last_name>\n  <image_url>/assets/user/default.png</image_url>\n
    # <birthday>2000-01-01</birthday>\n  <gender>gen</gender>\n  <bio>Bio</bio>\n  <location>Loc</location>\n  
    # <searchable>false</searchable>\n  <nsfw>true</nsfw>\n  <tag_string>#programming</tag_string>\n</profile></post>
    @classmethod
    def receive(cls, xml, c_from, u_to):
        from_addr = xml.xpath('//diaspora_handle')[0].text
        assert(from_addr == c_from.diasp.username)
        first_name = xml.xpath('//first_name')[0].text
        last_name = xml.xpath('//last_name')[0].text
        image_url = xml.xpath('//image_url')[0].text
        tags = xml.xpath('//tag_string')[0].text
        assert(False)


@diaspora_message_handler('/XML/post/retraction/type[text()="Person"]')
class Unsubscribe(MessageHandlerBase):
    @classmethod
    def receive(cls, xml, c_from, u_to):
        """
        Contact c_from has subcribed to u_to
        """
        from_addr = xml.xpath('//diaspora_handle')[0].text
        assert(from_addr == c_from.diasp.username)
        c_from.unsubscribe(u_to.contact)
