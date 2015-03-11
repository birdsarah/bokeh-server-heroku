from configure import configure_flask, make_tornado_app
from bokeh.server.app import app
from bokeh.server.configure import register_blueprint

configure_flask(config_file='config.py')
register_blueprint()
tornado_app = make_tornado_app(flask_app=app)
