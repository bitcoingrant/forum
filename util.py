"""
util.py 

System and convenience functions
"""
import re, os
import feedparser
import codecs

from flask import render_template, flash

# Regex matching substrings of alphanumeric plus spaces, dashes, and underscores
FILTER_ALPHANUMERIC = '[a-zA-Z0-9 \-\_]+'

MATCH_POST_TEXT = '^.{0,21600}$'
MATCH_ALPHANUMERIC = '^[a-zA-Z0-9 \-\_\.]+$'

def validate_input(data, *args):
    """ 
    Validate that a set of data contains the expected arguments in the provided format 

    Arguments -- 
        data -- flask form data dictionary-like object
        **args -- specifications of the form {'field_name': '<field_name>', 'regex': '<regex>' [, ...]}
        Required parameters:
            field_name: The name of a field expected in the data
            regex: a regex the field must match

        Recognized parameters:
            max_len: The maximum length of the data in the field
            min_len: The minimum length of the data in the field
            flash_err: An error to flash() if this parameter fails
    """
    for arg in args:
        if not arg['field_name'] in data:
            return False

        fail = False
        if not reg_check(arg['regex'], data[arg['field_name']], multiline=True):
            fail = True

        if arg.get('max_len') and len(data[arg['field_name']]) > arg.get('max_len'):
            fail = True

        if arg.get('min_len') and len(data[arg['field_name']]) < arg.get('min_len'):
            fail = True

        if fail:
            err_mess = arg.get('flash_error')
            if err_mess:
                flash(err_mess)
            return False

        return True


def reg_check(pattern, text, multiline=False):
    """ Check that a string contains a pattern match """
    if multiline:
        return re.match(pattern, text, flags=re.MULTILINE) != None
    else:
        return re.match(pattern, text) != None


def filter(pattern, text):
    """
    Returns the subset of the text matching the given regex

    Args:
        pattern -- The regular expression
        text -- The text to return the subset of
    """
    return ''.join(re.findall(pattern, text)) 


def find_threads(current_subforum='static'):
    """
     Return all files in the current directory
     ending in .rss. Threads are just rss feeds
    """
    threads = [feedparser.parse(os.path.join(current_subforum, x)) for x in reversed(sorted_ls(current_subforum)) if x[-4:] == '.rss']

    return threads


def find_subforums(current_subforum='static'):
    """ Return all non-special subdirectories, they are subforums """
    return [x for x in os.listdir(current_subforum) if os.path.isdir(os.path.join(current_subforum,x)) and not x in ('img','users', 'themes', 'lib', 'cgi-bin', 'templates', 'static') and x[0] != '.']

def subforums(current_subforum='static'):
    """
    Return a collection of subforum objects and metainfo
    """
    subforum_names = find_subforums(current_subforum=current_subforum)
    subforums = []
    for dir_name in subforum_names:

        subforum_info = {'name': dir_name}

        subforum_dir = os.path.join(current_subforum, dir_name)
        threads = find_threads(current_subforum=subforum_dir)

        subforum_info['num_threads'] = len(threads)

        subforums.append(subforum_info)

    return subforums


def filenameify(name):
    """
    Turns a human-provided filename into a nice-looking
    system filename
    """
    return name.lower().replace(' ', '_')


def sorted_ls(path):
    """ Returns a directory listing sorted. Thanks HarryM from StackOverflow """
    mtime = lambda f: os.stat(os.path.join(path, f)).st_mtime
    return list(sorted(os.listdir(path), key=mtime))


def render_thread_rss(thread_name, subforum, posts, title='', link=''):
    # We've got to lock the file before we write to it, we don't want 
    # simultaneous posts to cause conflicts

    #Stick the new entry to the beginning
    text = render_template('rss_template.rss', posts = posts, title = title, link = link)

    # Okay, I don't know exactly what stuff render_template can return,
    # but if everything's fine and dandy, it'll be unicode.
    # ofc, I should just go look this up. I think it'll throw an error
    # if something goes wrong, but who knows?
    # TODO: Read the source, Luke.
    if text.__class__.__name__ == 'unicode' and text:
        # DANGER TIME. Don't ctrl-c between these operations for now
        # or else stuff gets deleted <:-0
        # XXX: Fix dat.
        f = codecs.open(os.path.normpath('static' + subforum + '/' + thread_name+'.rss'), 'w', 'utf-8')
        f.write(text)
        f.close()

    else:
        print 'Thread writing failed:: render_thread_rss'
