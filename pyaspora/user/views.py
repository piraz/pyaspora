"""
Actions concerning a local User, who is mastered on this node.
"""

from flask import Blueprint

from pyaspora.database import db_session
from pyaspora.utils.validation import post_param
from pyaspora.utils.rendering import abort, render_response
from pyaspora.user import models

blueprint = Blueprint('users', __name__, template_folder='templates')

@blueprint.route('/login', methods=['GET'])
def login():
    return render_response('login_form.tpl')

@blueprint.route('/login', methods=['POST'])
def process_login():
    pass

@blueprint.route('/create', methods=['GET'])
def create_form():
    return render_response('create_form.tpl')

@blueprint.route('/create', methods=['POST'])
def create():
    """
    Create a new User (sign-up).
    """
    name = post_param('name', template='create_form.tpl')
    password = post_param('password', template='create_form.tpl')
    email = post_param('email', template='create_form.tpl')

    my_user = models.User()
    my_user.email = email
    print("realname is {}".format(str(name)))
    my_user.contact.realname = name
    my_user.generate_keypair(password)
    my_user.activate() # FIXME
    db_session.commit()
    return render_response('created.tpl')

@blueprint.route('/logout', methods=['GET'])
def logout():
    return render_response('logout.tpl')

@blueprint.route('/activate/<int:user_id>/<string:key_hash>', methods=['GET'])
def activate(user_id, key_hash):
    """
    Activate a user. This is intended to be a clickable link from the
    sign-up email that confirms the email address is valid.
    """
    matched_user = models.User.get_unactivated(user_id, key_hash)
    if not matched_user:
        abort(404, 'Not found')

    matched_user.activate()
    return render_response('activation_success.tpl')

@blueprint.route('/edit', methods=['GET'])
def edit_form():
    return render_response('edit.tpl')

@blueprint.route('/edit', methods=['POSTED'])
def edit():
    pass

# class User:
# 
#     @cherrypy.expose
#     def login(self, username=None, password=None):
#         """
#         Allow a user to log in.
#         """
#         if not(username and password):
#             return view.User.login(logged_in=User.logged_in())
#         user = model.User.get_by_email(username)
#         if not user:  # FIXME: if user is None or user.activated is None: (activated users only)
#             return view.User.login(error='Incorrect login details')
#         key = user.unlock_key_with_password(password)
#         if not key:
#             return view.User.login(error='Incorrect login details')
# 
#         # Stash the key in the session, protected by the session password
#         import pyaspora
#         cherrypy.session['logged_in_user'] = user.id
#         cherrypy.session['logged_in_user_key'] = key.exportKey(
#             passphrase=pyaspora.session_password)
#         self._show_my_profile(user)
# 
#     @classmethod
#     def _show_my_profile(cls, user=None):
#         if not user:
#             user = User.logged_in()
#         raise cherrypy.HTTPRedirect("/contact/profile?username={}".format(
#             quote_plus(user.contact.username)), 303)
# 
#     @cherrypy.expose
#     def logout(self):
#         """
#         Log out a user.
#         """
#         cherrypy.session.clear()
#         cherrypy.lib.sessions.expire()
#         return view.User.logged_out(logged_out=None)
# 
#     @classmethod
#     def logged_in(cls, required=False):
#         """
#         If a user session is active (the user is logged in), return the User
#         for the logged in user. Otherwise returns None.
#         """
#         try:
#             user_id = cherrypy.session.get("logged_in_user")
#             if user_id:
#                 return model.User.get(user_id)
#         except:
#             pass
# 
#         if required:
#             raise cherrypy.HTTPError(403, 'You must be logged in')
#         else:
#             return None
# 
#     @classmethod
#     def get_user_key(cls):
#         """
#         Get the session copy of the user's private key. If the session ID has
#         changed this may return None, in which case you'll need to ask the user
#         for their password again.
#         """
#         enc_key = cherrypy.session.get("logged_in_user_key")
#         if not enc_key:
#             return None
#         try:
#             import pyaspora
#             return RSA.importKey(enc_key, passphrase=pyaspora.session_password)
#         except (ValueError, IndexError, TypeError):
#             import traceback
#             traceback.print_exc()
#             return None
# 
#     @cherrypy.expose
#     def edit(self, bio=None, avatar=None):
#         logged_in = User.logged_in()
# 
#         saved = False
# 
#         if bio:
#             c = logged_in.contact
#             new_bio = c.bio
#             if not c.bio:
#                 new_bio = model.MimePart()
#                 session.add(new_bio)
#                 c.bio = new_bio
#             new_bio.type = 'text/plain'
#             new_bio.body = bio.encode('utf-8')
#             new_bio.text_preview = bio
#             session.add(c)
#             saved = True
# 
#         if saved:
#             session.commit()
#             self._show_my_profile(logged_in)
# 
#         return view.User.edit(logged_in=logged_in)
# 
#     @cherrypy.expose
#     def test(self):
#         """
#         temporary test of round-tripping the message builder and parser
#         """
#         #u = model.User.get(1)
#         #m = DiasporaMessageBuilder('Hello, world!', u)
#         #print(m.post('http://localhost:8080/receive/users/'+u.guid, u.contact, 'test'))
#         #return "OK"
#         #c = pyaspora.transport.diaspora.Transport.import_contact("lukeross@diasp.eu")
#         #session.add(c)
#         u = model.User.get(1)
#         c = model.Contact.get_by_username("lukeross@diasp.eu")
#         c.subscribe(u, "friend")
#         return "OK"
