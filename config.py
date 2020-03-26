import os
basedir = os.path.abspath(os.path.dirname(__file__))


class DevelopmentConfig(object):
    CLIENT_ID = "440148976425-33utej6ri23ksjuuatbnfbaqo8nt0ruu.apps.googleusercontent.com"
    CLIENT_SECRET = "6JA9YD0bwe3BialVcsiQ2oR1"
    REDIRECT_URI = 'https://127.0.0.1:5000/gCallback'
    AUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
    TOKEN_URI = 'https://accounts.google.com/o/oauth2/token'
    USER_INFO = 'https://www.googleapis.com/userinfo/v2/me'
    SCOPE = ['profile', 'email']
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'
    DEBUG = True
    TESTING = False
    CSRF_ENABLED = True
    SECRET_KEY = 'this-really-needs-to-be-changed'


class ProductionConfig(DevelopmentConfig):
    REDIRECT_URI = 'https://ulabsvotingspace.herokuapp.com/gCallback'
    SQLALCHEMY_DATABASE_URI = "postgres://sifnuyotpswqcu:3e6c5d3c3579caa654efae9ee886fce3ce6f020ec4afc8bbe28b1c7c4ff8e264@ec2-35-174-88-65.compute-1.amazonaws.com:5432/ddl6lhoj344ta"
