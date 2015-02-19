import os
from flask import Flask
from configure import configure_flask
from bokeh.server.app import bokeh_app

app = Flask("bokeh.server")

configure_flask(config_file='config.py')
app.register_blueprint(bokeh_app)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'mysecretkey')
