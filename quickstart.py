#!/usr/bin/python3

import cherrypy

from cherrypy.process import servers
def fake_wait_for_occupied_port(host, port): return
servers.wait_for_occupied_port = fake_wait_for_occupied_port


import pyaspora.controller
from pyaspora.controller.diaspora import diaspora_dispatcher
from pyaspora.tools.sqlalchemy import configure_session_for_app

app_config = {
    'tools.SATransaction.on': True,
    'tools.SATransaction.dburi': 'sqlite:///database.sqlite',
    'tools.SATransaction.echo': True,
    'tools.SATransaction.convert_unicode': True,

    'tools.sessions.on': True,
    'tools.sessions.timeout': 60,

    'tools.sessions.storage_type': "file",
    'tools.sessions.storage_path': "/home/lukeross/Development/Pyaspora/tmp/sessions",
    'tools.staticdir.root': "/home/lukeross/Development/Pyaspora/src/pyaspora/view"
    
}
app = cherrypy.tree.mount(pyaspora.controller.Root(), "/", config={
    '/': app_config,
    '/static': {
        'tools.staticdir.on': True,
        'tools.staticdir.dir': 'static'
    },
    '/.well-known/host-meta': {
        'request.dispatch': diaspora_dispatcher
    },
    '/receive': {
        'request.dispatch': diaspora_dispatcher
    },
    '/people': {
        'request.dispatch': diaspora_dispatcher
    }                                                                   
}) 
configure_session_for_app(app)

cherrypy.engine.subscribe('start', pyaspora.initialise_session_password)

if hasattr(cherrypy.engine, 'block'):
    # 3.1 syntax
    cherrypy.engine.start()
    cherrypy.engine.block()
else:
    # 3.0 syntax
    cherrypy.server.quickstart()
    cherrypy.engine.start()
