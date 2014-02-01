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
        if newname:
            group.name = newname
            session.commit()
            raise cherrypy.HTTPRedirect("/contact/friends?contactid={}".format(user.contact.id))
        else:
            return view.SubscriptionGroup.rename_form(group=group, logged_in=user)

