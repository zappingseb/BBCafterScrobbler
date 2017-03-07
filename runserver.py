"""
Flask App for BBC After Scrobbler

author: Sebastian Wolf
description: This is a flask app giving the ability to scrobble
    last.fm tracks from BBC Radio Shows

"""
__author__ = "Sebastian Wolf"
__copyright__ = "Copyright 2017, BBCAfterSCrobbler"
__license__ = "https://www.apache.org/licenses/LICENSE-2.0"
__version__ = "0.0.1"
__maintainer__ = "Sebastian Wolf"
__email__ = "sebastian@mail-wolf.de"
__status__ = "Production"

from os import environ
from FlaskWebProject1 import app
import logging

if __name__ == '__main__':
    HOST = environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    import logging


    handler = logging.FileHandler('app.log')  # errors logged to this file
    handler.setLevel(logging.WARN) # only log errors and above
    app.debug = True
    app.logger.addHandler(handler)
    app.run(HOST, PORT, debug=True)
