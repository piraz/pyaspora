import Crypto.Random

key = None

def initialise_key(k=None):
    global key
    if key is None:
        if k is not None:
            key = k
        else:
            key = Crypto.Random.get_random_bytes(64)