try:
    from urllib.parse import quote_plus  # py3
except:
    from urllib import quote_plus  # py2

import cherrypy
import cherrypy.lib.sessions

import pyaspora.model as model
import pyaspora.view as view

from pyaspora.tools.sqlalchemy import session


class User:
    """
    Actions concerning a local User, who is mastered on this node.
    """
    @cherrypy.expose
    def create(self, username=None, password=None, email=None, name=None):
        """
        Create a new User (sign-up).
        """
        if not(username and password and email and name):
            return view.User.create_form()

        my_user = model.User()
        my_user.email = email
        my_user.contact.username = username + '@localhost'
        my_user.contact.realname = name
        my_user.set_password(password)
        my_user.generate_keypair(password)
        return view.User.created()

    @cherrypy.expose
    def activate(self, guid):
        """
        Activate a user. This is intended to be a clickable link from the
        sign-up email that confirms the email address is valid.
        """
        matched_user = model.User.get_unactivated(guid)
        if not matched_user:
            return view.User.activation_failed()

        matched_user.activate()
        return view.User.activation_success()

    @cherrypy.expose
    def login(self, username=None, password=None):
        """
        Allow a user to log in.
        """
        if not(username and password):
            return view.User.login(logged_in=User.logged_in())
        user = model.User.get_by_email(username)
        if not user:  # FIXME: if user is None or user.activated is None: (activated users only)
            return view.User.login(error='Incorrect login details')
        key = user.unlock_key_with_password(password)
        if not key:
            return view.User.login(error='Incorrect login details')

        # Stash the key in the session, protected by the session password
        import pyaspora
        cherrypy.session['logged_in_user'] = user.id
        cherrypy.session['logged_in_user_key'] = key.exportKey(
            passphrase=pyaspora.session_password)
        self._show_my_profile(user)

    @classmethod
    def _show_my_profile(cls, user=None):
        if not user:
            user = User.logged_in()
        raise cherrypy.HTTPRedirect("/contact/profile?username={}".format(
            quote_plus(user.contact.username)), 303)

    @cherrypy.expose
    def logout(self):
        """
        Log out a user.
        """
        cherrypy.session.clear()
        cherrypy.lib.sessions.expire()
        return view.User.logged_out(logged_out=None)

    @classmethod
    def logged_in(cls, required=False):
        """
        If a user session is active (the user is logged in), return the User
        for the logged in user. Otherwise returns None.
        """
        try:
            user_id = cherrypy.session.get("logged_in_user")
            if user_id:
                return model.User.get(user_id)
        except:
            pass

        if required:
            raise cherrypy.HTTPError(403, 'You must be logged in')
        else:
            return None

    @classmethod
    def get_user_key(cls):
        """
        Get the session copy of the user's private key. If the session ID has
        changed this may return None, in which case you'll need to ask the user
        for their password again.
        """
        enc_key = cherrypy.session.get("logged_in_user_key")
        if not enc_key:
            return None
        try:
            import pyaspora
            key = RSA.importKey(enc_key, passphrase=pyaspora.session_password)
        except (ValueError, IndexError, TypeError):
            return None

    @cherrypy.expose
    def edit(self, bio=None, avatar=None):
        logged_in = User.logged_in()

        saved = False

        if bio:
            c = logged_in.contact
            new_bio = c.bio
            if not c.bio:
                new_bio = model.MimePart()
                session.add(new_bio)
                c.bio = new_bio
            new_bio.type = 'text/plain'
            new_bio.body = bio.encode('utf-8')
            new_bio.text_preview = bio
            session.add(c)
            saved = True

        if saved:
            session.commit()
            self._show_my_profile(logged_in)

        return view.User.edit(logged_in=logged_in)

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
    Actions/display relating to Contacts. These may be locally-mastered (who
    can also do User actions), but they may be Contacts on other nodes using
    cached information.
    """
    @cherrypy.expose
    def profile(self, username, full=None, perspective=None):
        """
        Display the "feed" for a Contact.
        """
        # Don't want a visitor to cause us to do lots of network access
        should_import = User.logged_in()

        contact = model.Contact.get_by_username(
            username, try_import=should_import)

        if not contact:
            return view.denied(status=404)

        if should_import:
            session.commit()  # in case imported

        posts = contact.feed
        posts = [p.post for p in posts if p.post.parent is None]
        formatted_posts = Post.format(posts, show_all=full)

        bio = None
        if contact.bio:
            try:
                bio = contact.bio.render_as('text/plain', inline=True)
            except:
                pass

        logged_in_user = User.logged_in()
        can_remove = False
        can_add = False
        can_post = False

        if not full:
            full = (logged_in_user and logged_in_user.contact.id == contact.id)

        if logged_in_user:
            can_remove = logged_in_user.subscribed_to(contact)
            can_add = (not(can_remove) and
                       logged_in_user.contact.id != contact.id)
            can_post = (can_remove or logged_in_user.contact.id == contact.id)

        return view.Contact.profile(
            contact=contact,
            posts=formatted_posts,
            can_add=can_add,
            can_remove=can_remove,
            can_post=can_post,
            logged_in=logged_in_user,
            bio=bio
        )

    @cherrypy.expose
    def find(self, search_term=None):
        """
        Search for a contact
        """
        pass

    @cherrypy.expose
    def subscribe(self, contactid, subtype='friend'):
        """
        Subscribe (form a friendship of some sort) with a Contact. This is a
        one-way relationship.
        """
        user = User.logged_in(required=True)
        contact = model.Contact.get(contactid)
        if not contact:
            return view.denied(status=404, reason='Contact cannot be found')
        contact.subscribe(user, subtype=subtype)
        session.commit()
        raise cherrypy.HTTPRedirect("/contact/profile?username={}".format(
            quote_plus(contact.username)))

    @cherrypy.expose
    def unsubscribe(self, contactid):
        """
        "Unfriend" a contact.
        """
        user = User.logged_in(required=True)
        contact = model.Contact.get(contactid)
        if not contact or not user.subscribed_to(contact):
            return view.denied(status=404,
                               reason='Subscription cannot be found')
        contact.unsubscribe(user)
        session.commit()
        raise cherrypy.HTTPRedirect("/contact/friends?contactid={}".format(
            user.contact.id))

    @cherrypy.expose
    def friends(self, contactid):
        """
        Show a Contact's friends/subscriptions list.
        """
        user = User.logged_in()
        contact = model.Contact.get(contactid)
        if not contact:
            return view.denied(status=404, reason='Contact cannot be found')
        is_friends_with = (user and user.subscribed_to(contact))
        public_view = not(user and user.contact.id == contact.id)
        return view.Contact.friend_list(
            contact=contact,
            public_view=public_view,
            is_friends_with=is_friends_with,
            logged_in=user
        )

    @cherrypy.expose
    def avatar(self, contactid):
        """
        Display the photo (or other media) that represents a Contact.
        """
        contact = model.Contact.get(contactid)
        if not contact:
            return view.denied(status=404, reason='No such user')

        part = contact.avatar
        if not part:
            return view.denied(status=404, reason='No such avatar')

        return view.raw(mime_type=part.type, body=part.body)

    @cherrypy.expose
    def groups(self, contactid, groups=None, newgroup=None):
        """
        Edit which SubscriptionGroups this Contact is in.
        """
        contact = model.Contact.get(contactid)
        if not contact:
            return view.denied(status=404, reason='No such user')

        user = User.logged_in(required=True)

        # Need to be logged in to create a post

        if not user.subscribed_to(contact):
            return view.denied(status=400,
                               reason='You are not subscribed to this contact')

        if groups:
            subtype = user.subscribed_to(contact).type

            if not isinstance(groups, list):
                groups = [groups]
            target_groups = set(groups)

            if newgroup:
                newgroup = newgroup.strip()

            if newgroup and 'new' in target_groups:
                new_group_obj = model.SubscriptionGroup.get_by_name(
                    user, newgroup, create=True)
                session.add(new_group_obj)
                session.commit()
                target_groups.add(new_group_obj.id)

            for group in user.groups:
                if group.id in target_groups:
                    group.add_contact(contact, subtype)

                else:
                    sub = group.has_contact(contact)
                    if sub:
                        session.delete(sub)

            session.commit()

            raise cherrypy.HTTPRedirect("/contact/friends?contactid={}".format(
                user.contact.id))

        group_status = dict([(g, g.has_contact(contact)) for g in user.groups])
        return view.Contact.edit_groups(logged_in=user, contact=contact,
                                        groups=group_status)


class System:
    @cherrypy.expose
    def initialise_database(self):
        """
        Install the database schema.

        FIXME - this should be a stand-alone script run by the server administrator.
        """
        model.Base.metadata.create_all()
        return "Tables created"


class Post:
    @cherrypy.expose
    def create(self, body=None, parent=None, share=None, share_level=None,
               walls_too=False, **kwargs):
        """
        Create a new Post and put it on my wall. May also put it on friends
        walls', depending on the Post's privacy level.
        """
        author = User.logged_in(required=True)
        walls_too = bool(walls_too)

        share_with_options = {
            'Groups': {"group-{}".format(g.id): g.name for g in author.groups},
            'Contacts': {"friend-{}".format(f.id): f.realname
                         for f in author.friends()},
        }
        for opt, subopt in share_with_options.items():
            if not subopt:
                del share_with_options[opt]
        share_with_options.update({
            'Me': None,
        })
        if parent:
            share_with_options.update({
                'PersonReplyingTo': None
            })

        # If the mandatory fields aren't supplied, we are probably creating a
        # new post
        if not body:
            return view.Post.create_form(parent=parent,
                                         share_with_options=share_with_options)

        post = model.Post(author=author.contact)

        # figure out if this is a comment on another post
        if parent:
            parent_post = model.Post.get(parent)
            # are we permitted to comment on it?
            if not(parent_post) or not(self.permission_to_view(parent_post)):
                return view.denied(status=403)
            if parent_post:
                post.parent = parent_post

        # prepare the MIME part and link it to the post
        part = model.MimePart(type='text/plain', body=body.encode('utf-8'),
                              text_preview=body)
        post.add_part(part, inline=True, order=1)

        # post to author's wall
        post.share_with([author.contact], show_on_wall=walls_too)

        if share_level.lower() == "group":
            for g in author.groups:
                if kwargs.get('group-{}'.format(g.id)):
                    post.share_with([s.contact for s in g.subscriptions],
                                    show_on_wall=walls_too)

        if walls_too or share_level.lower() == 'contacts':
            for f in author.friends():
                if share_level.lower() == 'contacts' and \
                        kwargs.get('friend-{}'.format(f.id)):
                    post.share_with([f], show_on_wall=walls_too)
                else:
                    # If I post it publicly on author's wall, all the contacts
                    # will see it, so ensure all the contacts get it.
                    post.share_with([f], show_on_wall=False)

        if share_level.lower() == 'personreplyingto' and parent_post:
            post.share_with([parent_post.author], show_on_wall=walls_too)

        # commit everything to get the Post ID
        session.commit()

        # done
        return view.Post.created(post=post)

    @classmethod
    def format(cls, posts, all_parts=False, show_all=False):
        """
        Convert a list of posts into a series of text/{html,plain} parts for
        web display.
        """
        formatted_posts = []
        for post in posts:
            to_display = []
            if Post.permission_to_view(post):
                for link in post.parts:
                    if link.inline:
                        try:
                            rendered = link.mime_part.render_as(
                                'text/html', inline=True)
                            to_display.append(
                                {'type': 'text/html', 'body': rendered})
                        except:
                            rendered = link.mime_part.render_as(
                                'text/plain', inline=True)
                            to_display.append(
                                {'type': 'text/plain', 'body': rendered})
                    elif (show_all):
                        to_display.append(
                            {'type': 'text/plain', 'body': 'Attachment'})
                formatted_post = {'post': post, 'formatted_parts': to_display}
                child_posts = post.children
                if child_posts:
                    shared_children = [p for p in child_posts]
                    formatted_post['children'] = cls.format(
                        shared_children, all_parts=all_parts, show_all=True)
                formatted_posts.append(formatted_post)
        return formatted_posts

    @cherrypy.expose
    def view(self, post_id):
        """
        Display a single post.
        """
        logged_in = User.logged_in()
        post = session.query(model.Post).get(post_id)
        if not self.permission_to_view(post):
            raise cherrypy.HTTPError(403)
        to_display = self.format([post], show_all=True)
        return view.Post.render(posts=to_display, logged_in=logged_in)

    @cherrypy.expose
    def raw_part(self, part_id):
        """
        Show a raw MIME part (such as an attachment) with no reformatting.
        """
        part = session.query(model.MimePart).get(part_id)
        if not part:
            raise cherrypy.HTTPError(404)

        # If anyone has shared this part with us (or the public), we get to
        # view it
        for link in part.posts:
            if self.permission_to_view(link.post):
                return view.raw(part.type, part.body)

        # Nobody shared it with us
        raise cherrypy.HTTPError(403)

    @classmethod
    def permission_to_view(cls, post, contact=None):
        """
        Can the contact <contact> (or the logged in user if not supplied) view
        this Post? Returns a boolean.
        """
        # Defaults to current logged in user
        if not contact:
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
        if not newname:
            return view.SubscriptionGroup.rename_form(
                group=group, logged_in=user)

        user = User.logged_in(required=True)
        group = model.SubscriptionGroup.get(groupid)
        if not group:
            raise cherrypy.HTTPError(404)
        if group.user_id != user.id:
            raise cherrypy.HTTPError(403)
        group.name = newname
        session.commit()
        raise cherrypy.HTTPRedirect("/contact/friends?contactid={}".format(
            user.contact.id))
