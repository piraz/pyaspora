from flask import request

from pyaspora.utils.rendering import abort


def post_param(name, optional=False, template=None):
    try:
        val = request.form[name]
        if not val and not optional:
            raise ValueError()
        return val
    except (KeyError, ValueError):
        if optional:
            return None
        abort(400, 'Missing value for: {0}'.format(name), template=template)


def check_attachment_is_safe(attachment):
    if attachment.mimetype == 'text/html' or \
            attachment.mimetype.startswith('application/x-pyaspora'):
        abort(400, 'Invalid upload')

    return True
