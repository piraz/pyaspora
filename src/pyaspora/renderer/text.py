import codecs

import pyaspora.renderer

class Plain(pyaspora.renderer.Renderer):
    def render_as_text_plain(self, part, inline=False):
        """
        Render a text/plain MIMEPart as text/plain - no interconversion required.
        """
        return codecs.utf_8_decode(part.body)[0]
    
class HTML(pyaspora.renderer.Renderer):
    def render_as_text_html(self, part, inline=False):
        """
        Render a text/html MIMEPart as text/html - no interconversion required.
        """
        return codecs.utf_8_decode(part.body)[0]