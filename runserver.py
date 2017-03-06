"""
This script runs the FlaskWebProject1 application using a development server.
"""


import pip
try:
 import six
except:
 package = 'six-1.10.0-py2.py3-none-any.whl'
 pip.main(['install', '--user', package])
 raise ImportError('Restarting')
try:
 import pylast
 from pylast import NetworkError, WSError
except:
 package = 'pylast'
 pip.main(['install', '--user', package])
 raise ImportError('Restarting')
try:
 from flask_wtf import FlaskForm
except:
 package = 'Flask-WTF'
 pip.main(['install', '--user', package])
 raise ImportError('Restarting')
try:
 from wtforms import DateField, SelectField, validators, ValidationError
except:
 package = 'WTForms'
 pip.main(['install', '--user', package])
 raise ImportError('Restarting')

try:
  import requests
  from requests.packages.urllib3.util.retry import Retry
  from requests.adapters import HTTPAdapter, ConnectionError
except:
 package = 'requests'
 pip.main(['install', '--user', package])
 raise ImportError('Restarting')
from os import environ
from FlaskWebProject1 import app

if __name__ == '__main__':
    try:
     from flask_wtf import FlaskForm
    except:
     package = 'Flask-WTF'
     pip.main(['install', '--user', package])
     raise ImportError('Restarting')
    HOST = environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.debug = True
    app.run(HOST, PORT,debug=True)
