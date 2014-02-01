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


