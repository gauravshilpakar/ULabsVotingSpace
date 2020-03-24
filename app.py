import requests
import datetime
import uuid
import json
from flask import Flask, render_template, redirect, request, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, form
from flask_login import LoginManager, login_required, login_user, logout_user, current_user, UserMixin

from oauthlib.oauth2 import WebApplicationClient
from requests_oauthlib import OAuth2Session
app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql+psycopg2://postgres:MHEECHA1lamo@localhost:5432/ulabsvotingspace"
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///test.db'
app.secret_key = str(uuid.uuid4())

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.session_protection = "strong"
login_manager.init_app(app)

# change this


class Auth:
    CLIENT_ID = "440148976425-33utej6ri23ksjuuatbnfbaqo8nt0ruu.apps.googleusercontent.com"
    CLIENT_SECRET = "6JA9YD0bwe3BialVcsiQ2oR1"
    REDIRECT_URI = 'https://127.0.0.1:5000/gCallback'
    AUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
    TOKEN_URI = 'https://accounts.google.com/o/oauth2/token'
    USER_INFO = 'https://www.googleapis.com/userinfo/v2/me'
    SCOPE = ['profile', 'email']

# client = WebApplicationClient(GOOGLE_CLIENT_ID)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def get_google_auth(state=None, token=None):
    if token:
        return OAuth2Session(Auth.CLIENT_ID, token=token)
    if state:
        return OAuth2Session(
            Auth.CLIENT_ID,
            state=state,
            redirect_uri=Auth.REDIRECT_URI)
    oauth = OAuth2Session(
        Auth.CLIENT_ID,
        redirect_uri=Auth.REDIRECT_URI,
        scope=Auth.SCOPE)
    return oauth


# class User(db.Model):
#     __tablename__ = 'users'
#     _id = db.Column(db.Integer, primary_key=True)
#     firstName = db.Column(db.String(100))
#     lastName = db.Column(db.String(100))
#     email = db.Column(db.String(100))
#     password = db.Column(db.String())
#     address = db.Column(db.String())
#     city = db.Column(db.String())
#     state = db.Column(db.String())
#     zip_ = db.Column(db.String())

#     def __init__(self, firstName, lastName, email, password, address, city, state, zip_):
#         self.firstName = firstName
#         self.lastName = lastName
#         self.email = email
#         self.password = password
#         self.address = address
#         self.city = city
#         self.state = state
#         self.zip_ = zip_

#     def serialize(self):
#         return {
#             'id': self._id,
#             'firstName': self.firstName,
#             'lastName': self.lastName,
#             'email': self.email,
#             "password": self.password,
#             "address": self.address,
#             "city": self.city,
#             "state": self.state,
#             "zip_": self.zip_
#         }

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    avatar = db.Column(db.String(200))
    active = db.Column(db.Boolean, default=False)
    tokens = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow())

# def get_google_provider_cfg():
#     return requests.get(GOOGLE_DISCOVERY_URL).json()


@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/login', methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    google = get_google_auth()
    auth_url, state = google.authorization_url(
        Auth.AUTH_URI, access_type='offline')
    session['oauth_state'] = state
    print(f"sesh: {session['oauth_state']}")
    return render_template('login.html', auth_url=auth_url)


@app.route('/gCallback')
def callback():
    # Redirect user to home page if already logged in.
    if current_user is not None and current_user.is_authenticated:
        return redirect(url_for('index'))
    if 'error' in request.args:
        if request.args.get('error') == 'access_denied':
            return 'You denied access.'
        return 'Error encountered.'
    if 'code' not in request.args and 'state' not in request.args:
        return redirect(url_for('login'))
    else:
        # Execution reaches here when user has
        # successfully authenticated our app.
        google = get_google_auth(state=session['oauth_state'])
        try:
            token = google.fetch_token(
                Auth.TOKEN_URI,
                client_secret=Auth.CLIENT_SECRET,
                authorization_response=request.url)
        except:
            return 'HTTPError occurred.'
        google = get_google_auth(token=token)
        resp = google.get(Auth.USER_INFO)
        if resp.status_code == 200:
            user_data = resp.json()
            email = user_data['email']
            user = User.query.filter_by(email=email).first()
            if user is None:
                user = User()
                user.email = email
            user.name = user_data['name']
            print(token)
            user.tokens = json.dumps(token)
            user.avatar = user_data['picture']
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('index'))
        return 'Could not fetch your information.'


@app.route("/index/")
def home():
    print(jsonify(session))
    return render_template("index.html")


# @app.route("/newaccount/", methods=["POST", "GET"])
# def newaccount():
#     if request.method == "POST":
#         firstName = request.form["firstName"]
#         lastName = request.form["lastName"]
#         email = request.form["email"]
#         password = request.form["password"]
#         address = request.form["address"]
#         city = request.form["city"]
#         state = request.form["state"]
#         zip_ = request.form["zip"]
#         newUser = User(firstName, lastName, email,
#                        password, address, city, state, zip_)
#         return newUser.serialize()
#     else:
#         return render_template("newaccount.html")

@app.route('/logout')
@login_required
def logout():
    logout_user()

    session.pop('access_token', None)
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(debug=True)
