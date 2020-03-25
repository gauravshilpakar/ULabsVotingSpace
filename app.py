import datetime
import json
import uuid

import requests
from flask import (
    Flask, jsonify, redirect, render_template, request, session, url_for)
from flask_admin import Admin, form
from flask_login import (
    LoginManager, UserMixin, current_user, login_required, login_user,
    logout_user)
from flask_sqlalchemy import SQLAlchemy
from oauthlib.oauth2 import WebApplicationClient
from requests.exceptions import HTTPError
from requests_oauthlib import OAuth2Session
from flask_admin.contrib.sqla import ModelView
app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = "postgres://sifnuyotpswqcu:3e6c5d3c3579caa654efae9ee886fce3ce6f020ec4afc8bbe28b1c7c4ff8e264@ec2-35-174-88-65.compute-1.amazonaws.com:5432/ddl6lhoj344ta"
# app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///test.db'
app.secret_key = str(uuid.uuid4())

admin = Admin(app)

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


class Videos(db.Model):
    _id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String())
    link = db.Column(db.String())
    votes = db.Column(db.Integer())

    def __init__(self, name, link):
        self.name = name
        self.link = link
        self.votes = votes

    def serialize(self):
        return{
            'name': self.name,
            'link': self.link,
            'votes': self.votes
        }

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


admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Videos, db.session))


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


@app.route('/login', methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    google = get_google_auth()
    auth_url, state = google.authorization_url(
        Auth.AUTH_URI, access_type='offline')
    session['oauth_state'] = state
    print(f"sesh:\n {session['oauth_state']}")
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
        # Execution reaches here when user has successfully authenticated our app.
        google = get_google_auth(state=session['oauth_state'])
        try:
            token = google.fetch_token(
                Auth.TOKEN_URI, client_secret=Auth.CLIENT_SECRET, authorization_response=request.url)
        except HTTPError:
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
            user.tokens = json.dumps(token)
            user.avatar = user_data['picture']
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('index'))
        return 'Could not fetch your information.'


@app.route('/', methods=["POST", "GET"])
def index():
    v_ = Videos.query.all()

    videos_json = [video.serialize() for video in v_]
    if request.method == "POST" and current_user.is_authenticated:
        return render_template("index.html", links=videos_json, authenticated=True)
    return render_template("index.html", links=videos_json)


@app.route("/newaccount/", methods=["POST", "GET"])
def newaccount():
    if request.method == "POST":
        firstName = request.form["firstName"]
        lastName = request.form["lastName"]
        email = request.form["email"]
        password = request.form["password"]
        address = request.form["address"]
        city = request.form["city"]
        state = request.form["state"]
        zip_ = request.form["zip"]
        newUser = User(firstName, lastName, email,
                       password, address, city, state, zip_)
        return newUser.serialize()
    else:
        return render_template("newaccount.html")


@app.route('/logout')
@login_required
def logout():
    session.pop('access_token', None)
    logout_user()
    return redirect(url_for('index'))


if __name__ == "__main__":
    # app.run(debug=True, ssl_context=('./ssl.crt', './ssl.key'))
    app.run(debug=True)
