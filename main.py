"""
main.py

Defines flask endpoints, and start flask development
server for the forum
"""
import os, sys
import uuid

from flask import Flask, render_template, redirect,\
    url_for, request, flash, session, send_from_directory, g

import util
import forum

from redis_sessions import RedisSessionInterface
from forms import NewThreadForm, LoginForm, SignupForm, ThreadReplyForm

app = Flask(__name__)

error_msg = None
try:
    app.session_interface = RedisSessionInterface()
except:
    sys.stderr.write("ERROR: Failed to connect to Redis")
    error_msg = "Failed to connect to Redis. Please contact server administrator"

try:
    app.config.from_pyfile('config.py')
except:
    sys.stderr.write("ERROR: Failed to read app config")
    error_msg = "Failed to load config. Please contact server administrator"


@app.template_global()
def get_app_config():
    """ Function to retrieve forum configuration in templates"""
    return app.config['FORUM_GLOBAL']


@app.template_global()
def get_login_nonce():
    return forum.get_nonce_message()


# Generate a new login nonce to sign after every GET request
@app.before_request
def generate_session_nonce():
    if request.method == 'GET':
        session['nonce'] = uuid.uuid4()
        g.login_form = LoginForm()


"""
@app.route('/robots.txt')
def static_from_root():
    Send robots.txt even if we don't have a webserver override
    serving files from /static
    return send_from_directory(app.static_folder, request.path[1:])
"""


# Webserver routes
@app.route('/<thread>', methods=['GET', 'POST'])
@app.route('/<thread>/<int:page>', methods=['GET', 'POST'])
def thread(thread=None, page=1, subforum='/'):
    """ Route for displaying and posting to a thread"""
    thread = util.filter(util.FILTER_ALPHANUMERIC, thread)

    if request.method == 'POST':
        return forum.reply_thread(thread,
                                  ThreadReplyForm(request.form),
                                  subforum)
    else:
        return forum.show_thread(thread, page, subforum)


@app.route('/<thread>/post/<int:post_num>', methods=['GET', 'POST'])
def thread_post(thread=None, post_num=1):
    thread_num = int(post_num / app.config['NUM_POSTS_PER_PAGE'])
    return redirect(url_for('thread', thread=thread_num) + '#' + str(post_num))


@app.route('/favicon.ico')
def favicon():
    """ Serve the favicon from the root directory """
    return redirect(url_for('static', filename='favicon.ico'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    """ Endpoint for the registration page and the registration form """
    if request.method == 'GET':
        return render_template('register.html', form=SignupForm())
    elif request.method == 'POST':
        return forum.register_username(SignupForm(request.form))


@app.route('/about', methods=['GET'])
def about():
    """ Route for the About page """
    return render_template('about.html')


@app.route('/login', methods=['POST'])
def login():
    print 'authenticating'
    return forum.authenticate(LoginForm(request.form))


@app.route('/logout')
def logout():
    """ Endpoint to end current user session """
    if session.get('authenticated') is True:
        flash('You have been logged out')

    session['authenticated'] = False
    session['username'] = None
    session['btc_addr'] = None
    return redirect('/')


def index(subforum=''):
    print "Subforum: " + subforum

    if request.method == 'POST':
        return forum.new_thread(NewThreadForm(request.form), subforum=subforum)

    # Figure out what threads and subforums we have
    # by looking at the directory tree
    threads = util.find_threads(current_subforum='static' + subforum)

    subforums = util.subforums(current_subforum='static' + subforum)

    # The directory tree to the current subforum
    return render_template('index.html', threads=threads,
                           subforums=subforums,
                           current_subforum='static' + subforum,
                           config=app.config['FORUM_GLOBAL'],
                           nonce=forum.get_nonce_message(),
                           form=NewThreadForm())

# Route the main page to the regular one if everything was okay with startup
# otherwise show an error page
if not error_msg:
    app.route('/', methods=['GET', 'POST'])(index)
else:
    app.route('/', methods=['GET', 'POST'])(lambda: (error_msg, 500))


def route_subforums(subroute='/', subforum_path='static'):
    """ Add routes for all subforums recursively """

    # Wrap route functions for a specific subforum route
    def wrap_index(subforum):
        return lambda: index(subforum)

    def wrap_thread(subforum):
        return lambda **kwargs: thread(thread=kwargs['thread'],
                                       subforum=subforum)

    def wrap_thread_page(subforum):
        return lambda **kwargs: thread(thread=kwargs['thread'],
                                       page=kwargs['page'],
                                       subforum=subforum)

    subforums = util.find_subforums(current_subforum=subforum_path)
    for forum in subforums:
        new_subroute = subroute + forum

        print "Routing to " + new_subroute
        app.add_url_rule(new_subroute,
                         (new_subroute).replace('/', '_') + '_index',
                         wrap_index(new_subroute),
                         methods=['GET', 'POST'])

        app.add_url_rule(subroute + forum + '/<thread>',
                         (subroute + forum).replace('/', '_') + 'thread',
                         wrap_thread(new_subroute),
                         methods=['GET', 'POST'])

        app.add_url_rule(new_subroute + '/<thread>/<int:page>',
                         (new_subroute).replace('/', '_') + 'thread_',
                         wrap_thread_page(new_subroute),
                         methods=['GET', 'POST'])

        route_subforums(subroute=new_subroute + '/',
                        subforum_path=os.path.join(subforum_path, forum))


route_subforums()

if __name__ == "__main__":
    app.run(debug=True)
