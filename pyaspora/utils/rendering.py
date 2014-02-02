from flask import jsonify, make_response, render_template, request, \
    abort as flask_abort, redirect as flask_redirect


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
    if 'status' not in data_structure:
        data_structure['status'] = 'OK'

    if output_format == 'json':
        response = make_response(jsonify(data_structure))
        response.output_format = 'json'
        return response
    else:  # HTML
        print(repr(data_structure))
        response = make_response(
            render_template(template_name, **data_structure))
        response.output_format = 'html'
        return response


def abort(status_code, message, extra={}, force_status=False,
          template='error.tpl'):
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
