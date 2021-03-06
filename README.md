The Bitcoin Grant Forum with BitAuth
------------------------------------


About BitAuth
-------

BitAuth is an authentication system that allows users to log in to web
services using their Bitcoin address by signing a one-time login message
with any of the major Bitcoin clients. 


Visit the forum
---------------

Check out the forum in action at [the Bitcoin grant](http://forums.bitcoingrant.com).

About the forum
---------------
This forum is at once a demo of BitAuth and the platform for discussion about its
development. It is loosely based on and inspired by the (NoNonsenseForum)[https://github.com/Kroc/NoNonsenseForum]

Installation
------------

This is WIP software. These instructions may not be up to date.

To install on Ubuntu, run:

`sudo apt-get install python-pip redis-server`

and then, in the project directory

`pip install -r requirements.txt`

The pip install from earlier should have given you Flask, and you can start the
cryptoapi/api on localhost:5000 with `python cryptoapi/api.py`

Once that's running, start the redis server on default `redis-server`

and, finally, you can try out the site on localhost with

`python main.py`

Running in a virtualenv is recommended

