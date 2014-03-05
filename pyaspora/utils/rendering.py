from __future__ import absolute_import

from dateutil.tz import tzlocal, tzutc
from flask import jsonify, make_response, render_template, request, url_for, \
    abort as flask_abort, redirect as flask_redirect
from lxml import etree


def _desired_format(default='html'):
    return request.args.get('alt', 'html')


def render_response(template_name, data_structure=None, output_format=None):
    """
    If the original request was for JSON, return the JSON data structure. If
    the desired format is HTML (the default) then pass the data structure
    to the template and render it.
    """
    if not output_format:
        output_format = _desired_format()

    if not data_structure:
        data_structure = {}

    if 'logged_in' not in data_structure:
        add_logged_in_user_to_data(data_structure)

    if 'status' not in data_structure:
        data_structure['status'] = 'OK'

    if output_format == 'json':
        response = make_response(jsonify(data_structure))
        response.output_format = 'json'
        return response
    else:  # HTML
        response = make_response(
            render_template(template_name, **data_structure))
        response.output_format = 'html'
        return response


def abort(status_code, message, extra={}, force_status=False,
          template=None):
    if not template:
        template = 'error.tpl'
    data = {
        'status': 'error',
        'code': status_code,
        'errors': [message]
    }
    data.update(extra)
    response = render_response(template, data)
    if force_status or response.output_format != 'html':
        response.status_code = status_code
    flask_abort(response)


def redirect(url, status_code=302, output_format=None, data_structure=None):
    if not output_format:
        output_format = _desired_format()

    if output_format == 'json':
        data = {
            'next_page': url
        }
        data.update(data_structure)
        return render_response(None, data, output_format='json')

    return flask_redirect(url, code=status_code)


def add_logged_in_user_to_data(data, user=False):
    from pyaspora.user.session import logged_in_user
    from pyaspora.user.views import json_user

    if user is False:
        user = logged_in_user()

    if user:
        base = json_user(user)
        if 'actions' not in base:
            base['actions'] = {}
        base['actions'].update({
            'logout': url_for('users.logout'),
            'feed': url_for('feed.view'),
            'new_post': url_for('posts.create'),
        })
    else:
        base = {
            'actions': {
                'login': url_for('users.login')
            }
        }

    data['logged_in'] = base


def send_xml(doc, content_type='text/xml'):
    """
    Utility function to return XML to the client. This is abstracted out
    so that pretty-printing can be turned on and off in one place.
    """
    response = make_response(etree.tostring(
        doc, xml_declaration=True, pretty_print=True, encoding="UTF-8"))
    response.headers['Content-Type'] = content_type
    return response


def ensure_timezone(dt):
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tzlocal())
    else:
        return dt
