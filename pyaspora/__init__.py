import os
from flask import Flask

from pyaspora.database import db
from pyaspora.contact.views import blueprint as contacts_blueprint
from pyaspora.roster.views import blueprint as roster_blueprint
from pyaspora.user.views import blueprint as user_blueprint

app = Flask(__name__)
db.init_app(app)
app.register_blueprint(contacts_blueprint, url_prefix='/contacts')
app.register_blueprint(roster_blueprint, url_prefix='/roster')
app.register_blueprint(user_blueprint, url_prefix='/users')


def init_db():
    db.create_all()


@app.route('/setup')
def setup():
    init_db()
    return "OK"
