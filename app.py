from configure import configure_flask
from bokeh.server.app import app
from bokeh.server.configure import make_tornado_app, register_blueprint

configure_flask(config_file='config.py')
register_blueprint()
tornado_app = make_tornado_app(flask_app=app)

