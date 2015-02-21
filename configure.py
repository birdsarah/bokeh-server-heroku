from __future__ import print_function
import logging
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

    bokeh_app.setup(
        backend,
        bbstorage,
        servermodel_storage,
        authentication,
    )
