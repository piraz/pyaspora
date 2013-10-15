import cherrypy

from jinja2 import Environment, FileSystemLoader

templ = Environment(loader=FileSystemLoader('src/pyaspora/view/templates'))


class _Template:
    def __init__(self, filename):
        self.filename = filename

    def __call__(self, **kwargs):
        return templ.get_template(self.filename).render(**kwargs)


def raw(mime_type, body):
    cherrypy.response.headers['Content-Type'] = mime_type
    return body


def denied(status=None, reason=None):
    if status:
        cherrypy.response.status = status
    return _Template('denied.tpl')(reason=reason)


class Contact:
    friend_list = _Template("contact/friend_list.tpl")
    profile = _Template("contact/profile.tpl")
    subscribed = _Template("contact/subscribed.tpl")
    edit_groups = _Template("contact/edit_groups.tpl")


class Post:
    create_form = _Template("post/create_form.tpl")
    created = _Template("post/created.tpl")
    render = _Template("post/render.tpl")


class SubscriptionGroup:
    rename_form = _Template("subscriptiongroup/rename.tpl")


class User:
    create_form = _Template("user/create_form.tpl")
    created = _Template("user/created.tpl")
    edit = _Template("user/edit.tpl")
    activation_failed = _Template("user/activation_failed.tpl")
    activation_success = _Template("user/activation_success.tpl")
    login = _Template("user/login.tpl")
    logged_out = _Template("user/logged_out.tpl")
