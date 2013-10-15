#!/usr/bin/python3

import cherrypy

import pyaspora.controller
#from pyaspora.transport.diaspora.controller import DiasporaDispatcher

from pyaspora.tools.sqlalchemy import configure_session_for_app

app_config = {
    'tools.SATransaction.on': True,
    'tools.SATransaction.dburi': 'sqlite:///database.sqlite',
    'tools.SATransaction.echo': True,
    'tools.SATransaction.convert_unicode': True,

    'tools.sessions.on': True,
    'tools.sessions.timeout': 60,

    'tools.sessions.storage_type': "file",
    'tools.sessions.storage_path': "/home/luke/Workspace/Pyaspora/tmp/sessions",
    'tools.staticdir.root': "/home/luke/Workspace/Pyaspora/src/pyaspora/view"
}
app = cherrypy.tree.mount(pyaspora.controller.Root(), "/", config={
    '/': app_config,
    '/static': {
        'tools.staticdir.on': True,
        'tools.staticdir.dir': 'static'
    },
    #'/.well-known': {
    #    'request.dispatch': DiasporaDispatcher()
    #},
    #'/receive': {
    #    'request.dispatch': DiasporaDispatcher()
    #},
    #'/people': {
    #    'request.dispatch': DiasporaDispatcher()
    #}
})
configure_session_for_app(app)

cherrypy.config.update({'server.socket_port': 8081})

cherrypy.engine.subscribe('start', pyaspora.initialise_session_password)

if hasattr(cherrypy.engine, 'block'):
    # 3.1 syntax
    cherrypy.engine.start()
    cherrypy.engine.block()
else:
    # 3.0 syntax
    cherrypy.server.quickstart()
    cherrypy.engine.start()
