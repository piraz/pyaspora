import re

class Renderer:
    """
    A base class for a series of classes that can render a MIME part into a variety of
    commonly-used output formats (eg. HTML snippets, plain text) by specifying a
    desired target MIME type.
    """
    @classmethod      
    def render(cls, part, to_type, inline=False):
        """
        Attempt to render MIMEPart <part> into MIME type <to_type> (a string). If <inline> is true,
        the part will be rendered as part of a document and the rendering should be suitable
        for in-line display. Otherwise the MIMEPart is being displayed stand-alone.
        
        May throw an exception of the rendering cannot be completed or there is no suitable
        handler for the MIME part installed.
        """
        # "text/plain" => ("text", "plain")
        (first_mime_part, second_mime_part) = part.type.split("/")
        
        # Strip out any invalid characers in the first part.
        first_mime_part = re.sub(r'[^A-Za-z0-9]', '', first_mime_part)
        
        # ...and the second. Camel-case around any we find
        # (eg. "x-foo-bar" becomes "xFooBar")
        second_mime_part = re.sub(r'[^A-Za-z0-9]', '', second_mime_part.title())
        
        # Attempt to find a handling class (eg. "pyspora.renderer.text.Plain")
        __import__("pyaspora.renderer." + first_mime_part)
        final_renderer = getattr(globals()[first_mime_part], second_mime_part)()
        
        # And let it process the part
        return final_renderer.render_as(part, to_type, inline)
        
    def render_as(self, part, to_type, inline=False):
        """
        Attempt to render MIMEPart <part> into MIME type <to_type>.
        
        May throw an exception if the Renderer implementation cannot render the
        part to type <to_type>.
        """
        
        # This fallback implementation attempts to call a specific function for to_type.
        # For example, if to_type is "text/plain", it tries to call "render_as_text_plain" 
        (first_mime_part, second_mime_part) = to_type.split("/")
        
        # Sanitise the two MIME parts
        first_mime_part = re.sub(r'[^A-Za-z0-9]', '', first_mime_part)
        second_mime_part = re.sub(r'[^A-Za-z0-9]', '', second_mime_part)
        
        # And invoke the method
        return getattr(self, "render_as_" + first_mime_part + "_" + second_mime_part)(part, inline)
    
    def render_as_text_plain(self, part, inline=False):
        """
        Default handler for Renderers that don't implement a specific way of rendering
        to text/plain - this retrieves the pre-cooked text implementation stored at MIMEPart
        creation time.
        """
        return part.text_preview