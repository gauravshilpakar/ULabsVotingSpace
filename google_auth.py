import functools
import os

import flask
import google.oauth2.credentials
import googleapiclient.discovery
from authlib.integrations.requests_client import OAuth2Session


from config import *

ACCESS_TOKEN_URI = 'https://www.googleapis.com/oauth2/v4/token'
AUTHORIZATION_URL = 'https://accounts.google.com/o/oauth2/v2/auth?access_type=offline&prompt=consent'

AUTHORIZATION_SCOPE = 'openid email profile'

AUTH_REDIRECT_URI = ProductionConfig.FN_AUTH_REDIRECT_URI
BASE_URI = ProductionConfig.FN_BASE_URI
CLIENT_ID = ProductionConfig.FN_CLIENT_ID
CLIENT_SECRET = ProductionConfig.FN_CLIENT_SECRET

AUTH_TOKEN_KEY = 'auth_token'
AUTH_STATE_KEY = 'auth_state'

app = flask.Blueprint('google_auth', __name__)


def is_logged_in():
    return True if AUTH_TOKEN_KEY in flask.session else False


def build_credentials():
    if not is_logged_in():
        raise Exception('User must be logged in')

    oauth2_tokens = flask.session[AUTH_TOKEN_KEY]

    return google.oauth2.credentials.Credentials(
        oauth2_tokens['access_token'],
        refresh_token=oauth2_tokens['refresh_token'],
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_uri=ACCESS_TOKEN_URI)


def get_user_info():
    credentials = build_credentials()

    oauth2_client = googleapiclient.discovery.build(
        'oauth2', 'v2',
        credentials=credentials)

    return oauth2_client.userinfo().get().execute()


def no_cache(view):
    @functools.wraps(view)
    def no_cache_impl(*args, **kwargs):
        response = flask.make_response(view(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    return functools.update_wrapper(no_cache_impl, view)


@app.route('/google/login')
@no_cache
def google_login():
    from app import Users, db
    state = None
    while state is None:
        google_session = OAuth2Session(CLIENT_ID, CLIENT_SECRET,
                                       scope=AUTHORIZATION_SCOPE,
                                       redirect_uri=AUTH_REDIRECT_URI)
        uri, state = google_session.create_authorization_url(AUTHORIZATION_URL)
        flask.session[AUTH_STATE_KEY] = state

    print(f"\n\nGoogle Auth State: \n\n{state}\n\n")
    # flask.session.permanent = True

    try:
        user_info = get_user_info()
        email = user_info['email']
        user = Users.query.filter_by(email=email).first()

        print(f"\n\n\n{user}\n\n\n")
        if user is None:
            user = Users(email=user_info['email'],
                         name=user_info['name'],
                         avatar=user_info['picture'])

        db.session.add(user)
        db.session.commit()
    except:
        return flask.redirect(uri, code=302)
    return flask.redirect(uri, code=200)


@app.route('/google/auth')
@no_cache
def google_auth_redirect():
    req_state = flask.request.args.get('state', default=None, type=None)

    try:
        if req_state != flask.session[AUTH_STATE_KEY]:
            return flask.redirect(flask.url_for('index'))
    except:
        pass
    session = OAuth2Session(CLIENT_ID, CLIENT_SECRET,
                            scope=AUTHORIZATION_SCOPE,
                            state=flask.session[AUTH_STATE_KEY],
                            redirect_uri=AUTH_REDIRECT_URI)

    oauth2_tokens = session.fetch_access_token(
        ACCESS_TOKEN_URI,
        authorization_response=flask.request.url)

    flask.session[AUTH_TOKEN_KEY] = oauth2_tokens

    return flask.redirect(flask.url_for('index'))


@app.route('/google/logout')
@no_cache
def google_logout():
    flask.session.pop(AUTH_TOKEN_KEY, None)
    flask.session.pop(AUTH_STATE_KEY, None)

    return flask.redirect(flask.url_for('index'), code=302)
