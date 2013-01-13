import urllib.parse

import cherrypy.lib.sessions
from jinja2 import Environment, FileSystemLoader

import pyaspora.model as model
import pyaspora.transport.diaspora.controller
from pyaspora.tools.sqlalchemy import session

# Quick access to the templating engine
templ = Environment(loader=FileSystemLoader('src/pyaspora/templates'))

class User:
    """
    Actions concerning a local User, who is mastered on this node.
    """
    @cherrypy.expose
    def create(self, username=None, password=None, email=None, name=None):
        """
        Create a new User (sign-up).
        """
        if username is None or password is None or email is None or name is None:
            return templ.get_template("user/create_form.tpl").render()
        else:
            my_user = model.User()
            my_user.email = email
            my_user.contact.username = username+'@localhost'
            my_user.contact.realname = name
            my_user.set_password(password)
            my_user.generate_keypair(password)
            return templ.get_template("user/created.tpl").render()
        
    @cherrypy.expose
    def activate(self, guid):
        """
        Activate a user. This is intended to be a clickable link from the sign-up email
        that confirms the email address is valid.
        """
        matched_user = model.User.get_unactivated(guid) 
        if (matched_user is None):
            return templ.get_template("user/activation_failed.tpl").render()
        else:
            matched_user.activate()
            return templ.get_template("user/activation_success.tpl").render()
        
    @cherrypy.expose
    def login(self, username=None, password=None):
        """
        Allow a user to log in.
        """
        if username is None or password is None:
            return templ.get_template("user/login.tpl").render({ 'logged_in': User.logged_in() })
        user = model.User.get_by_email(username)
        if user is None: # FIXME: if user is None or user.activated is None: (activated users only)
            return templ.get_template("user/login.tpl").render({ 'error': 'Incorrect login details' })
        if not user.password_is(password):
            return templ.get_template("user/login.tpl").render({ 'error': 'Incorrect login details' })
        cherrypy.session['logged_in_user'] = user.id
        raise cherrypy.HTTPRedirect("/contact/profile?username=" + urllib.parse.quote_plus(user.contact.username), 303)
          
    @cherrypy.expose
    def logout(self):
        """
        Log out a user.
        """
        cherrypy.session.clear()
        cherrypy.lib.sessions.expire()
        return templ.get_template("user/logged_out.tpl").render({ 'logged_out': None })
    
    @classmethod
    def logged_in(cls):
        """
        If a user session is active (the user is logged in), return the User for the logged
        in user. Otherwise returns None.
        """
        try:
            user_id = cherrypy.session.get("logged_in_user")
            if user_id is None:
                return None
            return model.User.get(user_id)
        except:
            return None
        
    @cherrypy.expose
    def test(self):
        """
        temporary test of round-tripping the message builder and parser
        """
        #u = model.User.get(1)
        #m = DiasporaMessageBuilder('Hello, world!', u)
        #print(m.post('http://localhost:8080/receive/users/'+u.guid, u.contact, 'test'))
        #return "OK"
        #c = pyaspora.transport.diaspora.Transport.import_contact("lukeross@diasp.eu")
        #session.add(c)
        u = model.User.get(1)
        c = model.Contact.get_by_username("lukeross@diasp.eu")
        c.subscribe(u, "friend")
        return "OK"
    
class Contact:
    """
    Actions/display relating to Contacts. These may be locally-mastered (who can also do
    User actions), but they may be Contacts on other nodes using cached information.
    """
    @cherrypy.expose
    def profile(self, username, full=None, perspective=None):
        """
        Display the "feed" for a Contact.
        """
        contact = model.Contact.get_by_username(username)
        
        # Don't want a visitor to cause us to do lots of network access
        if contact is None and User.logged_in():
            try:
                contact = model.Contact()
                pyaspora.transport.Diaspora.import_contact(username, contact)
                session.add(contact)
            except:
                contact = None
        
        if contact is None:
            cherrypy.response.status = 404
            return templ.get_template("denied.tpl").render()
            
        posts = contact.feed
        posts = [ p.post for p in posts if p.post.parent is None ]
        formatted_posts = Post.format(posts, show_all=full) 
        
        logged_in_user = User.logged_in()
        can_remove = False
        can_add = False
        can_post = False
        
        if full is None:
            full = (logged_in_user and logged_in_user.contact.id == contact.id)
        
        if logged_in_user is not None:
            can_remove = logged_in_user.subscribed_to(contact)        
            can_add = (not(can_remove) and logged_in_user.contact.id != contact.id)
            can_post = (can_remove or logged_in_user.contact.id == contact.id)

        return templ.get_template("contact/profile.tpl").render({
            'contact': contact,
            'posts': formatted_posts,
            'can_add': can_add,
            'can_remove': can_remove,
            'can_post': can_post,
            'logged_in': logged_in_user
        })
    
    @cherrypy.expose
    def find(self, search_term=None):
        """
        Search for a contact
        """
        pass
    
    @cherrypy.expose
    def subscribe(self, contactid, subtype='friend'):
        """
        Subscribe (form a friendship of some sort) with a Contact. This is a one-way relationship.
        """
        user = User.logged_in()
        if user is None:
            cherrypy.response.status = 403
            return templ.get_template("denied.tpl").render({ 'reason': 'You must be logged in to subscribe' })
        contact = model.Contact.get(contactid)
        if contact is None:
            cherrypy.response.status = 404
            return templ.get_template("denied.tpl").render({ 'reason': 'Contact cannot be found' })
        contact.subscribe(user, subtype=subtype)
        session.commit()
        return templ.get_template("contact/subscribed.tpl").render()

    def unsubscribe(self, contactid):
        """
        "Unfriend" a contact.
        """
        user = User.logged_in()
        if user is None:
            cherrypy.response.status = 403
            return templ.get_template("denied.tpl").render({ 'reason': 'You must be logged in to subscribe' })
        contact = model.Contact.get(contactid)
        if not user.subscribed_to(contact):
            cherrypy.response.status = 404
            return templ.get_template("denied.tpl").render({ 'reason': 'Contact cannot be found' })
        contact.transport().unsubscribe(user)
        session.commit()
        return templ.get_template("contact/unsubscribed.tpl").render()
    
    def groups(self, contactid, groups=[]):
        pass
    
    @cherrypy.expose
    def friends(self, contactid):
        """
        Show a Contact's friends/subscriptions list.
        """
        user = User.logged_in()
        contact = model.Contact.get(contactid)
        if contact is None:        
            cherrypy.response.status = 404
            return templ.get_template("denied.tpl").render({ 'reason': 'Cannot find contact' })
        is_friends_with = (user is not None and user.subscribed_to(contact))
        public_view = not(user is not None and user.contact.id == contact.id)
        return templ.get_template("contact/friend_list.tpl").render({
            'contact': contact, 
            'public_view': public_view,
            'is_friends_with': is_friends_with,
            'logged_in': user
        })
        
    @cherrypy.expose
    def avatar(self, contactid):
        """
        Display the photo (or other media) that represents a Contact.
        """
        contact = model.Contact.get(contactid)
        if contact is None:
            cherrypy.response.status = 404
            templ.get_template("denied.tpl").render({ 'reason': 'No such user' })
        
        part = contact.avatar
        if part is None:
            cherrypy.response.status = 404
            templ.get_template("denied.tpl").render({ 'reason': 'No such part' })
            
        cherrypy.response.headers['Content-Type'] = part.type
        return part.body        
        
class System:
    @cherrypy.expose
    def initialise_database(self):
        """
        Install the database schema.
        
        FIXME - this should be a stand-alone script run by the server administrator.
        """
        model.Base.metadata.create_all()
        levels = { 
            'hidden': 'Not shown at all',
            'self': 'Only shown to me',
            'contacts': 'Only shown to my contacts',
            'public': 'Shown to everyone'
        }
        for k, v in levels.items():
            session.add(model.PrivacyLevel(level=k, description=v))
        session.commit()
        return "Tables created"

class Post:
    @cherrypy.expose
    def create(self, body=None, privacy=None, parent=None, canreshare=False):
        """
        Create a new Post and put it on my wall. May also put it on friends walls', depending
        on the Post's privacy level.
        """
        author = User.logged_in()
        
        # Need to be logged in to create a post
        if author is None:
            cherrypy.response.status = 403
            return templ.get_template("denied.tpl").render({ 'reason': 'You must be logged in to post' })
        
        # If the mandatory fields aren't supplied, we are probably creating a new post
        if body is None or privacy is None:
            levels = model.PrivacyLevel.all()
            return templ.get_template("post/create_form.tpl").render({ 'privacy': levels, 'parent': parent })

        # figure out if this is a comment on another post
        parent_post = None
        if parent is not None:
            parent_post = model.Post.get(parent)
            # are we permitted to comment on it?
            if not(parent_post) or not(self.permission_to_view(parent_post)):
                cherrypy.response.status = 403
                return templ.get_template("denied.tpl").render()
        
        post = model.Post(author=author.contact, permits_reshare=canreshare)
        if parent_post:
            post.parent = parent_post        
        
        # prepare the MIME part and link it to the post
        part = model.MimePart(type='text/plain', body=body.encode('utf-8'), text_preview=body)
        post.add_part(part, inline=True, order=1)
        
        # post to author's wall
        post.share_with([author.contact], privacy)
        
        if (privacy in ('public', 'contacts')):
            post.share_with(author.friends(), privacy)
        
        # commit everything to get the Post ID
        session.commit()
        
        # done
        return templ.get_template("post/created.tpl").render({ 'post': post })
    

    
    @classmethod
    def format(cls, posts, all_parts=False, show_all=False):
        """
        Convert a list of posts into a series of text/{html,plain} parts for web display
        """
        user = User.logged_in()
        formatted_posts = []
        for post in posts:
            authored_by_me = False
            to_display = []
            if user:
                authored_by_me = (post.author == user.contact)
            if (show_all or authored_by_me) and Post.permission_to_view(post):
                for link in post.parts:
                    if link.inline:
                        try:
                            rendered = link.part.render_as('text/html', inline=True)
                            to_display.append({ 'type': 'text/html', 'body': rendered })
                        except:
                            rendered = link.part.render_as('text/plain', inline=True)
                            to_display.append({ 'type': 'text/plain', 'body': rendered })                    
                    elif (show_all):
                        to_display.append({ 'type': 'text/plain', 'body': 'Attachment' })
                formatted_post = { 'post': post, 'formatted_parts': to_display }
                child_posts = post.children
                if child_posts:
                    shared_children = [p for p in child_posts]
                    formatted_post['children'] = cls.format(shared_children, all_parts=all_parts, show_all=True) 
                formatted_posts.append(formatted_post)
        return formatted_posts 

    @cherrypy.expose
    def view(self, post_id):
        """
        Display a single post.
        """
        post = session.query(model.Post).get(post_id)
        if not self.permission_to_view(post):
            cherrypy.response.status = 403
            return templ.get_template("denied.tpl").render()
        to_display = self.format([post], show_all=True)
        return templ.get_template("post/render.tpl").render({ 'post': post, 'parts': to_display })
            

    @cherrypy.expose
    def raw_part(self, part_id):
        """
        Show a raw MIME part (such as an attachment) with no reformatting.
        """
        part = session.query(model.MimePart).get(part_id)
        if part is None:
            cherrypy.response.status = 404
            templ.get_template("denied.tpl").render({ 'reason': 'No such part' })
            
        # If anyone has shared this part with us (or the public), we get to view it
        for link in part.posts:
            if self.permission_to_view(link.post):
                cherrypy.response.headers['Content-Type'] = part.type
                return part.body

        # Nobody shared it with us
        cherrypy.response.status = 403
        return templ.get_template("denied.tpl").render({ 'reason': 'Permission denied' })
    
    @classmethod
    def permission_to_view(cls, post, contact=None):
        """
        Can the contact <contact> (or the logged in user if not supplied) view this Post?
        Returns a boolean.
        """
        # Defaults to current logged in user
        if contact is None:
            user = User.logged_in()
            if user is not None:
                contact = user.contact            
        return post.has_permission_to_view(contact)

class SubscriptionGroup:
    """
    Actions relating to a named group of friends/contacts (a "circle" in G+)
    """
    @cherrypy.expose
    def rename(self, groupid, newname=None):
        """
        Give a group a new name.
        """

        user = User.logged_in()
        if user is None:
            cherrypy.response.status = 403
            return templ.get_template("denied.tpl").render({ 'reason': 'You must be logged in to subscribe' })
        group = model.SubscriptionGroup.get(groupid)        
        if group is None:
            cherrypy.response.status = 404
            return templ.get_template("denied.tpl").render({ 'reason': 'No such group' })        
        if group.user_id != user.id:
            cherrypy.response.status = 403
            return templ.get_template("denied.tpl").render({ 'reason': "You don't own this group" })
        if newname is not None:
            group.name = newname
            session.commit()
            return templ.get_template("subscriptiongroup/renamed.tpl").render({ 'logged_in': user })
        else:
            return templ.get_template("subscriptiongroup/rename.tpl").render({ 'group': group, 'logged_in': user })

 
class Root:
    """
    Top level of the website.
    """
    user = User()
    contact = Contact()
    system = System()
    post = Post()
    subscriptiongroup = SubscriptionGroup()
    diaspora = pyaspora.transport.diaspora.controller.DiasporaController()
    
    @cherrypy.expose   
    def index(self):
        """
        A welcome-and-sign-up page.
        """
        return "Nothing to see - yet"