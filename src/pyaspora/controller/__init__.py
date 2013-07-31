import cherrypy
from pyaspora.controller import website, diaspora

class Root:
    """
    Top level of the website.
    """
    user = website.User()
    contact = website.Contact()
    system = website.System()
    post = website.Post()
    subscriptiongroup = website.SubscriptionGroup()
    diaspora = diaspora.DiasporaController()
    
    @cherrypy.expose   
    def index(self):
        """
        A welcome-and-sign-up page.
        """
        return "Nothing to see - yet"