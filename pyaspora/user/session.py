from Crypto.PublicKey import RSA
from flask import current_app, session

from pyaspora.user.models import User


def logged_in_user():
    user_id = session.get('user_id', None)
    if not user_id:
        return None

    private_key = session.get('key', None)
    if not private_key:
        return None

    user = User.get(user_id)
    if not user:
        return None

    try:
        user._unlocked_key = RSA.importKey(private_key,
                                           passphrase=current_app.secret_key)
        return user
    except (ValueError, IndexError, TypeError):
        return None


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
