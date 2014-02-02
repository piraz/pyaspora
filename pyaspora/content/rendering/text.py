import codecs

from pyaspora.content.rendering import Renderer


class Plain(Renderer):
    def render_as_text_plain(self, part, inline=False):
        """
        Render a text/plain MIMEPart as text/plain - no interconversion
        required.
        """
        return codecs.utf_8_decode(part.body)[0]


class HTML(Renderer):
    def render_as_text_html(self, part, inline=False):
        """
        Render a text/html MIMEPart as text/html - no interconversion required.
        """
        return codecs.utf_8_decode(part.body)[0]
