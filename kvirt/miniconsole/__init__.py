# coding=utf-8

import functools
from kvirt.bottle import Bottle, static_file, jinja2_view, response, redirect
from kvirt.common import get_free_port
from kvirt.defaults import FAKECERT
import os
from shutil import which
from time import sleep


class Kminiconsole():

    def __init__(self, config, port, name):
        self.port = port
        app = Bottle()

        app = Bottle()
        basedir = f"{os.path.dirname(Bottle.run.__code__.co_filename)}/web"
        view = functools.partial(jinja2_view, template_lookup=[f"{basedir}/templates"])

        @app.route('/static/<filename:path>')
        def server_static(filename):
            return static_file(filename, root=f'{basedir}/static')

        @app.route("/")
        @view('console.html')
        def vmconsole():
            k = config.k
            password = ''
            scheme = 'ws://'
            if which('websockify') is None:
                response.status = 404
                return "missing websockify binary on server side"
            consoleurl = k.console(name, tunnel=config.tunnel, web=True)
            if consoleurl.startswith('spice') or consoleurl.startswith('vnc'):
                protocol = 'spice' if consoleurl.startswith('spice') else 'vnc'
                websocketport = get_free_port()
                host, port = consoleurl.replace('%s://' % protocol, '').split(':')
                websocketcommand = "websockify %s -vD --idle-timeout=30 %s:%s" % (websocketport, host, port)
                if config.type == 'ovirt':
                    port, password = port.split('+')
                    if protocol == 'spice':
                        scheme = 'ws://'
                        cert = os.path.expanduser('~/.kcli/websockify.pem')
                        if not os.path.exists(cert):
                            with open(cert, 'w') as f:
                                f.write(FAKECERT)
                        websocketcommand = f"websockify {websocketport} -vD --idle-timeout=30"
                        websocketcommand += f" --cert {cert} --ssl-target {host}:{port}"
                    else:
                        websocketcommand = "websockify {websocketport} -vD --idle-timeout=30 {host}:{port}"
                os.popen(websocketcommand)
                sleep(5)
                return {'protocol': protocol, 'title': 'Vm console', 'port': websocketport, 'password': password,
                        'scheme': scheme}
            elif consoleurl is not None:
                return redirect(consoleurl)
            else:
                response.status = 404
                return "consoleurl couldnt be evaluated"

        self.app = app

    def run(self):
        data = {'host': '0.0.0.0', 'port': self.port}
        self.app.run(**data)
