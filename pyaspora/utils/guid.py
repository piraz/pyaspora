from flask import current_app
from hashlib import sha512


def guid_base():
    return sha512(current_app.secret_key.encode('ascii')).hexdigest()


def guid(obj_type, obj_id):
    return "{0}-{1}-{2}".format(guid_base(), obj_type, obj_id)
