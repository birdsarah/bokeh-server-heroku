import os, urlparse
redis_url = urlparse.urlparse(os.environ.get('REDISCLOUD_URL', '127.0.0.1:6397'))

pub_zmqaddr = "ipc:///tmp/0"
sub_zmqaddr = "ipc:///tmp/1"
run_forwarder = True
model_backend = {'type' : 'redis',
                 'redis_host': redis_url.hostname,
                 'redis_port' : redis_url.port,
                 'redis_password' : redis_url.password,
                 'start-redis' : False}
secret_key = os.environ.get('BOKEH_SECRET_KEY', 'another secret key')
multi_user = False
scripts = [
    'blueprints/sliders_app_hbox.py',
    'blueprints/washmap_app.py',
]
