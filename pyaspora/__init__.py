import base64
import Crypto.Random
import os
from flask import Flask

from pyaspora.contact.views import blueprint as contacts_blueprint
from pyaspora.user.views import blueprint as user_blueprint
from pyaspora.database import db_session, init_db

app = Flask(__name__)
app.register_blueprint(contacts_blueprint, url_prefix='/contacts')
app.register_blueprint(user_blueprint, url_prefix='/users')
app.secret_key = os.urandom(24)

session_password = None

def initialise_session_password(password='foo'):
    global session_password
    if not session_password:
        session_password = password or \
            base64.b64encode(Crypto.Random.get_random_bytes(64))

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()
    
@app.route('/setup')
def setup():
    init_db()
    return "OK"