from flask import current_app
from hashlib import sha512


def guid_base():
    return sha512(current_app.secret_key.encode('ascii')).hexdigest()


def make_guid(obj_type, obj_id):
    return "{0}-{1}-{2}".format(guid_base(), obj_type, obj_id)


def parse_guid(guid, obj_type):
    try:
        guid_base, parsed_type, obj_id = guid.split('-')
    except ValueError:
        return None
    if guid_base != guid_base():
        return None
    if parsed_type != obj_type:
        return None
    return obj_id
