import sqlalchemy
 
import Crypto.Random

session_key = None

def initialise_session_key(k=None):
    global session_key
    if session_key is None:
        if k is not None:
            session_key = k
        else:
            session_key = Crypto.Random.get_random_bytes(64)
