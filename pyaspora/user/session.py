from __future__ import absolute_import

from functools import wraps
from Crypto.PublicKey import RSA
from flask import current_app, session

from pyaspora.user.models import User
from pyaspora.utils.rendering import abort


def logged_in_user(fetch=True):
    user_id = session.get('user_id', None)
    if not user_id:
        return None

    private_key = session.get('key', None)
    if not private_key:
        return None

    try:
        unlocked_key = RSA.importKey(private_key,
                                     passphrase=current_app.secret_key)
    except (ValueError, IndexError, TypeError):
        return None

    if not fetch:
        return True

    user = User.get(user_id)
    user._unlocked_key = unlocked_key
    return user


def require_logged_in_user(fn):
    @wraps(fn)
    def _inner(*args, **kwargs):
        user = logged_in_user()
        if not user:
            abort(401, 'Not logged in')
        return fn(*args, _user=user, **kwargs)
    return _inner


def log_in_user(email, password):
    user = User.get_by_email(email)
    if not user:
        return None

    if not user.activated:
        return None

    key = user.unlock_key_with_password(password)
    if not key:
        return None

    user._unlocked_key = key
    session['user_id'] = user.id
    session['key'] = key.exportKey(format='PEM', pkcs=1,
                                   passphrase=current_app.secret_key)

    return user
