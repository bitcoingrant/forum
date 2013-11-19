# config file for PyNoNonsenseForum
FORUM_GLOBAL = {
    'lock_posts': False,
    'lock_threads': False,
    'MAX_POST_LENGTH': 21600
}

PORT = 9090
SERVER_NAME = 'localhost:9090'
SECRET_KEY = 'Seriously dude change this to a randomly generated string ieDu3xai vaileGh5 eib2Aich Ususie8b'

MODE='http'

SITE_ROOT = MODE + '://' + SERVER_NAME 
HOST = '0.0.0.0'
COIN_API = 'http://localhost:5000'
# Not including the title post
NUM_POSTS_PER_PAGE = 19
