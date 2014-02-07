import os
from flask import Flask, url_for

from pyaspora.database import db
from pyaspora.content.views import blueprint as content_blueprint
from pyaspora.contact.views import blueprint as contacts_blueprint
from pyaspora.feed.views import blueprint as feed_blueprint
from pyaspora.post.views import blueprint as posts_blueprint
from pyaspora.roster.views import blueprint as roster_blueprint
from pyaspora.tag.views import blueprint as tags_blueprint
from pyaspora.user.views import blueprint as users_blueprint
from pyaspora.utils import templates

app = Flask(__name__)
db.init_app(app)

# Global configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Register modules
app.register_blueprint(content_blueprint, url_prefix='/content')
app.register_blueprint(contacts_blueprint, url_prefix='/contacts')
app.register_blueprint(feed_blueprint, url_prefix='/feed')
app.register_blueprint(posts_blueprint, url_prefix='/posts')
app.register_blueprint(roster_blueprint, url_prefix='/roster')
app.register_blueprint(tags_blueprint, url_prefix='/tags')
app.register_blueprint(users_blueprint, url_prefix='/users')

# Global template utility functions
app.jinja_env.globals.update(chunk_url_params=templates.chunk_url_params)


def init_db():
    db.create_all()


@app.route('/setup')
def setup():
    init_db()
    return "OK"


@app.route('/')
def index():
    from pyaspora.user.session import logged_in_user
    from pyaspora.utils.rendering import redirect
    if logged_in_user():
        return redirect(url_for('feed.view'))
    else:
        return redirect(url_for('users.login'))
