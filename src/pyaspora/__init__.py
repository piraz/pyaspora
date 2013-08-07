import base64
import sqlalchemy
 
import Crypto.Random

session_password = None

def initialise_session_password(password=None):
    global session_password
    if not session_password:
        session_password = password or \
            base64.b64encode(Crypto.Random.get_random_bytes(64))
