import os
from flask import Flask
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from pyaspora.database import db
from pyaspora.content.views import blueprint as content_blueprint
from pyaspora.contact.views import blueprint as contacts_blueprint
from pyaspora.feed.views import blueprint as feed_blueprint
from pyaspora.post.views import blueprint as posts_blueprint
from pyaspora.roster.views import blueprint as roster_blueprint
from pyaspora.user.views import blueprint as users_blueprint

app = Flask(__name__)
db.init_app(app)
app.register_blueprint(content_blueprint, url_prefix='/content')
app.register_blueprint(contacts_blueprint, url_prefix='/contacts')
app.register_blueprint(feed_blueprint, url_prefix='/feed')
app.register_blueprint(posts_blueprint, url_prefix='/posts')
app.register_blueprint(roster_blueprint, url_prefix='/roster')
app.register_blueprint(users_blueprint, url_prefix='/users')

def _chunk_url_params(url):
    url_parts = list(urlsplit(url))
    qs_parts = parse_qsl(url_parts[3])
    print("qs={}".format(repr(qs_parts)))
    url_parts[3] = ''
    return (urlunsplit(url_parts), qs_parts)
    
app.jinja_env.globals.update(chunk_url_params=_chunk_url_params)


def init_db():
    db.create_all()


@app.route('/setup')
def setup():
    init_db()
    return "OK"
