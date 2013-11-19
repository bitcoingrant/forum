"""
forum.py

Defines all the forum operation functions
"""
import feedparser
import requests
import json
import uuid
import math
import os
import markdown

from datetime import datetime
from flask import render_template, redirect, url_for, abort, request, flash, session
from lockfile import FileLock
from xml.sax.saxutils import unescape

import util

from forms import NewThreadForm, ThreadReplyForm


def get_session_nonce():
    """
        Returns the session nonce, and generates it anew
        for GETs
    """
    if not session.get('nonce'):
        session['nonce'] = uuid.uuid4()
    return session['nonce']


def get_nonce_message():
    """
    Returns the message that the user is supposed to sign
    """
    return 'site-auth-data::'+str(get_session_nonce())+':'


def check_sig(message, signature, btc_addr):
    from main import app

    resp = requests.post(app.config['COIN_API']+'/check_sig',
                         {'signature': signature,
                             'message': message,
                             'btc_addr': btc_addr})
    if resp.ok:
        return resp.text
    else:
        return None


def show_thread(thread_name, page, subforum='/'):
    from main import app

    """ Render and return the html of the given page of the given thread """
    thread = feedparser.parse(os.path.normpath('static' + subforum + '/' + thread_name+'.rss'))

    # If it doesn't load succesfully, 404
    if not thread.feed:
        abort(404)

    op = thread.entries[-1]
    title = op.title
    start_post = (page-1)*app.config['NUM_POSTS_PER_PAGE'] + 1
    end_post = (page)*app.config['NUM_POSTS_PER_PAGE'] + 1
    #TODO: Reversing doesn't scale
    replies = [x for x in reversed(thread.entries)][start_post:end_post]

    numpages = int(math.ceil((len(thread.entries) - 1) / float(app.config['NUM_POSTS_PER_PAGE'])))

    return render_template('thread.html',
                            thread = thread,
                            thread_name = thread_name,
                            replies = enumerate(replies),
                            op = op,
                            title = op.title,
                            unescape = unescape,
                            page = page,
                            markdown = markdown.markdown,
                            numpages = numpages,
                            form=ThreadReplyForm())


#XXX: Use redis for the userlist, or a public rss feed?
def set_btc_addr(username, btc_addr):
    """ Atomically add a user to the userlist file """
    lock = FileLock('userlist')
    with lock:
        try:
            f = open('users.json', 'r')
            users = f.read()
            f.close()
        except:
            users = ''
        if not users:
            users = '{}'
        users = json.loads(users)

        # No matching user found, add 'im
        users[username] = {'btc_addr':btc_addr}

        f = open('users.json', 'w')
        f.write(json.dumps(users))
        f.close()


def get_userlist():
    """ Get the list of users from the users.json file """
    lock = FileLock('userlist')

    with lock:
        try:
            f = open('users.json', 'r')
            users = f.read()
            f.close()
        except:
            users = ''
        if not users:
            users = '{}'
        users = json.loads(users)

        return users


def reply_thread(thread_name, form, subforum='/'):
    """ Takes user data from flask.form, checks it, and adds the reply to the target thread """
    from main import app

    if app.config['FORUM_GLOBAL'].get('lock_posts'):
        flash('Posting is locked')
        return redirect(url_for('thread', thread=thread_name))

    # Check if the data is fine, otherwise bail
    if not form.validate():
        return redirect(url_for('thread', thread=thread_name))

    if not session.get('authenticated'):
        flash('Log in to reply')
        return redirect(url_for('thread', thread=thread_name))

    # Okay, we're going to rerender the whole goddamn file. This is inefficient, we'll
    # figure out a better and less lazy way of doing this later
    lock = FileLock(thread_name + '.lock')
    with lock:
        thread = feedparser.parse(os.path.normpath('static' + subforum + '/' + thread_name+'.rss'))

        title = thread.feed.title
        link = thread.feed.link

        entry = {
            # Jinja rendering should escape this as unsafe
            'description' : form.text.data,
            'title': 'RE [{}]: {}'.format(len(thread.entries) + 1, thread.feed.title),
            'author' : session['username'],
            'published' : str(datetime.now()), #TODO: Date formatting
            'link': '',
            'bit_btcaddress': session['btc_addr'],
        }

        util.render_thread_rss(thread_name, subforum,
                [entry] + thread.entries, title=title, link=link)
    # Just redirect to the the root page for now
    return redirect('/')


def new_thread(form, subforum):
    """ Create a new thread rss file in the /static folder """
    from main import app
    
    if not form.validate():
        flash('Invalid input')
        return redirect('/')

    # TODO: support new threads in subforums
    # TODO: Make this have fewer side effects. Return messages to flash?
    if not session.get('authenticated'):
        flash('You must be logged in to post')
        return redirect('/') 

    if app.config['FORUM_GLOBAL'].get('lock_threads'):
        flash('Thread creation is locked')
        return redirect('/')

    # Make sure the title has some characters we're okay with for a filename
    title = util.filter(util.FILTER_ALPHANUMERIC, form.title.data)
    if not title:
        flash('Input consisted of invalid characters')
        return redirect('/')

    thread_name = util.filenameify(title)

    lock = FileLock('.' + subforum + thread_name)
    with lock:

        if thread_name in util.find_subforums('static'+subforum):
            flash('A thread with that name already exists')
            return redirect('/')

        link = app.config['SITE_ROOT'] + subforum + '/' + thread_name 
        entry = {
            # Jinja rendering should escape this as unsafe
            'description' : form.text.data, 
            'title': title,
            'author' : session['username'],
            'published' : str(datetime.now()),
            'link': app.config['SITE_ROOT'] + subforum + thread_name + '#1',
            'bit_btcaddress': session['btc_addr'], 
        }

        if not entry['description']:
            # TODO: Check if abort plays nice with the with-based lock.
            print "Failblog"
            abort(400)

        util.render_thread_rss(thread_name, subforum, 
                [entry], title, link=link)

    # This is annoying, but just redirect to the root page for now
    flash('Your post went through!')
    return redirect('/')


def authenticate(form):
    """ Log in an existing user """

    if not form.validate():
        flash('Invalid input')
        return redirect('/')

    sig = form.signature.data
    message = get_nonce_message()
    username = form.username.data

    users = get_userlist()
    print users
    if not username in users:  
        flash('The provided username is unregistered. Sign up!')
        return redirect('/register')

    btc_addr = users[username].get('btc_addr')

    if not check_sig(message, sig, btc_addr):
        print 'Sig check fail {} {} {}'.format(message, sig, btc_addr)
        flash('Signature check failed. Did you copy the supplied text exactly?')
        return redirect('/')

    print btc_addr

    session['authenticated'] = True 
    session['username'] = username 
    session['btc_addr'] = btc_addr
    flash('Authenticated!')
    return redirect('/')


def register_username(form):
    """ Register a new user """

    if not form.validate():
        flash('Invalid input')
        return redirect('/register')

    # site-auth-data::uuid4():
    sig = form.signature.data
    message = get_nonce_message()
    btc_addr = form.btc_addr.data
    username = form.username.data

    users = get_userlist()
    if username in users:  
        flash('That username is already taken')
        return redirect(url_for('register'))

    if not check_sig(message, sig, btc_addr):
        print 'Sig check fail {} {} {}'.format(nonce, sig, btc_addr)
        flash('Signature check failed. Did you copy the the supplied text exactly?')
        return redirect(url_for('register'))

    set_btc_addr(username, btc_addr)

    session['authenticated'] = True 
    session['username'] = username 
    session['btc_addr'] = btc_addr
    print 'Registered user ' + username
    flash('Congratulations, you\'re registered!')
    return redirect('/')

