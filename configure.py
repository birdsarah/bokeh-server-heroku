from __future__ import print_function
import logging
log = logging.getLogger(__name__)

from os.path import dirname
import imp
import sys

from six.moves.queue import Queue

from bokeh.server.app import bokeh_app
from bokeh.server.configure import StaticFilter
from bokeh.server.server_backends import (
    InMemoryServerModelStorage,
    MultiUserAuthentication, RedisServerModelStorage, ShelveServerModelStorage,
    SingleUserAuthentication,
)
from bokeh.server.serverbb import (
    InMemoryBackboneStorage, RedisBackboneStorage, ShelveBackboneStorage
)
from bokeh.server.settings import settings as server_settings
from bokeh.server.zmqpub import Publisher

from tornado.web import Application, FallbackHandler
from tornado.wsgi import WSGIContainer

from bokeh.server import websocket
##bokeh_app is badly named - it's really a blueprint
from bokeh.server.app import app
from bokeh.server.models import convenience as mconv
from bokeh.server.models import docs
from bokeh.server.zmqsub import Subscriber
from bokeh.server.forwarder import Forwarder

from threading import Thread
import zmq

timeout = 0.1


def configure_flask(config_argparse=None, config_file=None, config_dict=None):
    if config_argparse:
        server_settings.from_args(config_argparse)
    if config_dict:
        server_settings.from_dict(config_dict)
    if config_file:
        server_settings.from_file(config_file)
    for handler in logging.getLogger().handlers:
        handler.addFilter(StaticFilter())
    # must import views before running apps
    from bokeh.server.views import deps
    backend = server_settings.model_backend
    if backend['type'] == 'redis':
        import redis
        rhost = backend.get('redis_host', '127.0.0.1')
        rport = backend.get('redis_port', 6379)
        rpass = backend.get('redis_password')
        bbdb = backend.get('backbone_storage_db_id')
        smdb = backend.get('servermodel_storage_db_id')
        bbstorage = RedisBackboneStorage(
            redis.Redis(host=rhost, port=rport, password=rpass, db=bbdb)
        )
        servermodel_storage = RedisServerModelStorage(
            redis.Redis(host=rhost, port=rport, password=rpass, db=smdb)
        )
    elif backend['type'] == 'memory':
        bbstorage = InMemoryBackboneStorage()
        servermodel_storage = InMemoryServerModelStorage()

    elif backend['type'] == 'shelve':
        bbstorage = ShelveBackboneStorage()
        servermodel_storage = ShelveServerModelStorage()

    if not server_settings.multi_user:
        authentication = SingleUserAuthentication()
    else:
        authentication = MultiUserAuthentication()
    bokeh_app.url_prefix = server_settings.url_prefix
    bokeh_app.publisher = Publisher(server_settings.ctx,
                                    server_settings.pub_zmqaddr, Queue())

    for script in server_settings.scripts:
        script_dir = dirname(script)
        if script_dir not in sys.path:
            print("adding %s to python path" % script_dir)
            sys.path.append(script_dir)
        print("importing %s" % script)
        imp.load_source("_bokeh_app", script)

    log.warning('Setup')
    bokeh_app.setup(
        backend,
        bbstorage,
        servermodel_storage,
        authentication,
    )


class MySubscriber(object):
    def __init__(self, ctx, addrs, wsmanager):
        self.ctx = ctx
        self.addrs = addrs
        self.wsmanager = wsmanager
        self.kill = False
        self.timer = 0
        self.keep_message = None

    def run(self):
        sockets = []
        poller = zmq.Poller()
        for addr in self.addrs:
            socket = self.ctx.socket(zmq.SUB)
            socket.connect(addr)
            socket.setsockopt_string(zmq.SUBSCRIBE, u"")
            sockets.append(socket)
            poller.register(socket, zmq.POLLIN)
        try:
            while not self.kill:
                socks = dict(poller.poll(timeout * 1000))
                self.timer += 1
                if self.timer > 100:
                    log.warning(self.timer)
                    msg = self.keep_message
                    topic, msg, exclude = msg['topic'], msg['msg'], msg['exclude']
                    self.wsmanager.send(topic, msg, exclude=exclude)
                    self.timer = 0
                for socket, v in socks.items():
                    msg = socket.recv_json()
                    self.keep_message = msg
                    topic, msg, exclude = msg['topic'], msg['msg'], msg['exclude']
                    self.wsmanager.send(topic, msg, exclude=exclude)
        except zmq.ContextTerminated:
            pass
        finally:
            for s in sockets:
                s.close()

    def start(self):
        self.thread = Thread(target=self.run)
        self.thread.start()

    def stop(self):
        self.kill = True


class SBTA(Application):
    def __init__(self, flask_app, **settings):
        self.flask_app = flask_app
        tornado_flask = WSGIContainer(flask_app)
        url_prefix = server_settings.url_prefix
        handlers = [
            (url_prefix + "/bokeh/sub", websocket.WebSocketHandler),
            (r".*", FallbackHandler, dict(fallback=tornado_flask))
        ]
        super(SBTA, self).__init__(handlers, **settings)
        self.wsmanager = websocket.WebSocketManager()

        def auth(auth, docid):
            #HACKY
            if docid.startswith("temporary-"):
                return True
            doc = docs.Doc.load(bokeh_app.servermodel_storage, docid)
            status = mconv.can_read_doc_api(doc, auth)
            return status
        self.wsmanager.register_auth('bokehplot', auth)
        log.warning('CONN')

        self.subscriber = MySubscriber(server_settings.ctx,
                                       [server_settings.sub_zmqaddr],
                                       self.wsmanager)
        if server_settings.run_forwarder:
            self.forwarder = Forwarder(server_settings.ctx,
                                       server_settings.pub_zmqaddr,
                                       server_settings.sub_zmqaddr)
        else:
            self.forwarder = None

    def start_threads(self):
        bokeh_app.publisher.start()
        self.subscriber.start()
        if self.forwarder:
            self.forwarder.start()

    def stop_threads(self):
        bokeh_app.publisher.stop()
        self.subscriber.stop()
        if self.forwarder:
            self.forwarder.stop()


def make_tornado_app(flask_app=None):
    if flask_app is None:
        flask_app = app
    if server_settings.debug:
        flask_app.debug = True
    flask_app.secret_key = server_settings.secret_key
    tornado_app = SBTA(flask_app, debug=server_settings.debug)
    tornado_app.start_threads()
    return tornado_app
