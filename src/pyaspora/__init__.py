import sqlalchemy
 
import Crypto.Random

session_key = None

def initialise_session_key(k=None):
    global session_key
    if not session_key:
        session_key = k or Crypto.Random.get_random_bytes(64)
