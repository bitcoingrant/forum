from flask_wtf import Form
from wtforms import TextField
from wtforms.validators import DataRequired, Length, Regexp, AnyOf, Optional
import config


class NewThreadForm(Form):
    title = TextField('title',   validators=[Length(
        min=1, max=config.FORUM_GLOBAL.get('MAX_TITLE_LENGTH', 160)), DataRequired()])
    text = TextField('text', validators=[Length(
        min=0, max=config.FORUM_GLOBAL.get('MAX_POST_LENGTH', 21600)), DataRequired()])
    # Silly botspam protection
    email = TextField('Email Address', validators=[AnyOf(['example@abc.com'])])


class ThreadReplyForm(Form):
    text = TextField('text', validators=[Length(
        min=0, max=config.FORUM_GLOBAL.get('MAX_POST_LENGTH', 21600)), DataRequired()])
    # Silly botspam protection
    email = TextField('Email Address', validators=[AnyOf(['example@abc.com'])])


class LoginForm(Form):
    username = TextField('Username', validators=[DataRequired(), Length(
        min=1, max=config.FORUM_GLOBAL.get('MAX_USERNAME_LENGTH', 66))])
    signature = TextField('Login Message Signature', validators=[
                          DataRequired(), Regexp('^\s*[0-9a-zA-Z\+/=]{88}\s*$')])


class SignupForm(Form):
    username = TextField('Username', validators=[DataRequired(), Length(
        min=1, max=config.FORUM_GLOBAL.get('MAX_USERNAME_LENGTH', 66))])
    signature = TextField('Login Message Signature',
                          validators=[Regexp('^\s*[0-9a-zA-Z\+/=]{88}\s*')])
    btc_addr = TextField('Bitcoin address', validators=[DataRequired()])
    auth_nonce = TextField('Sign this message', validators=[Optional()])
