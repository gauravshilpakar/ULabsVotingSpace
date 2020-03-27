import datetime
import json
import os
import uuid

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import requests
from flask import (
    Flask, jsonify, redirect, render_template, request, session, url_for)
from flask_admin import Admin, form
from flask_admin.contrib.sqla import ModelView
from flask_login import (
    LoginManager, UserMixin, current_user, login_required, login_user,
    logout_user)
from flask_sqlalchemy import SQLAlchemy
from oauthlib.oauth2 import WebApplicationClient
from requests.exceptions import HTTPError
from requests_oauthlib import OAuth2Session
from config import *

import google_auth

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["SQLALCHEMY_DATABASE_URI"] = ProductionConfig.SQLALCHEMY_DATABASE_URI
app.secret_key = str(uuid.uuid4())
app.register_blueprint(google_auth.app)

admin = Admin(app)
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.session_protection = "strong"
login_manager.init_app(app)


class Videos(db.Model, UserMixin):
    _id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String())
    link = db.Column(db.String())
    votes = db.Column(db.Integer(), default=0)

    def __init__(self, name, link):
        self.name = name
        self.link = link
        self.votes = votes

    def serialize(self):
        return{
            '_id': self._id,
            'name': self.name,
            'link': self.link,
            'votes': self.votes
        }


class Users(db.Model, UserMixin):
    _id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    avatar = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow())

    def __init__(self, email=None, name=None, avatar=None):
        self.email = email
        self.name = name
        self.avatar = avatar


admin.add_view(ModelView(Users, db.session))
admin.add_view(ModelView(Videos, db.session))


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


# def get_google_auth(state=None, token=None):
#     if token:
#         return OAuth2Session(ProductionConfig.CLIENT_ID, token=token)
#     if state:
#         return OAuth2Session(
#             ProductionConfig.CLIENT_ID,
#             state=state,
#             redirect_uri=ProductionConfig.REDIRECT_URI)
#     oauth = OAuth2Session(
#         ProductionConfig.CLIENT_ID,
#         redirect_uri=ProductionConfig.REDIRECT_URI,
#         scope=ProductionConfig.SCOPE)
#     return oauth


@app.route('/login/', methods=["GET", "POST"])
def login():
    return render_template("login.html", doc="Login!")


@app.route("/google/login")
def loginwithgoogle():
    return google_auth.google_login()


# @app.route('/gCallback')
# def callback():
#     if current_user is not None and current_user.is_authenticated:
#         return redirect(url_for('index'))
#     if 'error' in request.args:
#         if request.args.get('error') == 'access_denied':
#             return 'You denied access.'
#         return 'Error encountered.'
#     if 'code' not in request.args and 'state' not in request.args:
#         return redirect(url_for('login'))
#     else:
#         google = get_google_auth(state=session['oauth_state'])
#         # try:
#         token = google.fetch_token(
#             ProductionConfig.TOKEN_URI,
#             client_secret=ProductionConfig.CLIENT_SECRET,
#             authorization_response=request.url)
#         # except HTTPError:
#         #     return 'HTTPError occurred.'
#         google = get_google_auth(token=token)
#         resp = google.get(ProductionConfig.USER_INFO)
#         if resp.status_code == 200:

#             return redirect(url_for('index'))
#         return 'Could not fetch your information.'


@app.route('/', methods=["POST", "GET"])
def index():
    v_ = Videos.query.all()
    videos_json = [video.serialize() for video in v_]
    if request.method == "POST" and google_auth.is_logged_in():
        return render_template("index.html",
                               links=videos_json,
                               google_authenticated=True,
                               authenticated=True,
                               doc="ULabs Voting Space",
                               user_info=google_auth.get_user_info())
    elif request.method == "POST" and not google_auth.is_logged_in():
        return redirect(url_for('login'))

    elif google_auth.is_logged_in():
        return render_template("index.html",
                               links=videos_json,
                               doc="ULabs Voting Space",
                               google_authenticated=True,
                               user_info=google_auth.get_user_info())
    else:
        return render_template("index.html",
                               links=videos_json,
                               doc="ULabs Voting Space",
                               google_authenticated=False,
                               )


@app.route('/thankyou/', methods=['POST', 'GET'])
def thankyou():
    if request.method == "GET":
        return redirect(url_for('index', doc="Thank You!"))
    else:
        selected_id = request.form['radio']
        selected_video = Videos.query.get(int(selected_id))
        selected_video.votes += 1
        db.session.commit()

        print("\n\n\nPost Commit")
        print(selected_video.name)
        print(selected_video.votes)

        return render_template("thankyou.html",
                               doc="Thank You!",
                               google_authenticated=True,
                               user_info=google_auth.get_user_info())


@app.route('/logout')
@login_required
def logout():
    return redirect(url_for('google_logout'))


@app.route("/results/")
def results():
    if google_auth.is_logged_in():
        return render_template('results.html',
                               doc="Poll Results",
                               google_authenticated=True,
                               user_info=google_auth.get_user_info())

    return render_template('results.html',
                           doc="Poll Results",)


dash_app = dash.Dash(__name__,
                     server=app,
                     url_base_pathname='/dash-app/',
                     external_stylesheets=[dbc.themes.DARKLY])

theme = {
    'dark': False,
    'detail': '#007439',
    'primary': '#00EA64',
    'secondary': '#6E6E6E'
}


def get_videos():
    videos = Videos.query.all()
    video_name = [vid.name for vid in videos]
    video_votes = [vid.votes for vid in videos]

    return video_name, video_votes


def return_layout():
    name, votes = get_videos()
    return html.Div(
        children=[
            dcc.Graph(id='example', figure={
                'data': [{'x': name, 'y': votes, 'type': 'bar', 'name': 'Plots'}],
                'layout': {
                    'title': 'Video Poll Results'}}
            )])


dash_app.layout = return_layout


@app.route('/dash/')
def dash():
    return redirect('/dash-app/')


if __name__ == "__main__":
    # app.run(debug=True, ssl_context=('./ssl.crt', './ssl.key'))
    app.run(debug=True)


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
