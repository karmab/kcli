from flask import Flask
from flask import render_template, request, jsonify
from glob import glob
from kvirt.common import get_overrides
import os
import re


class Kexposer():
    def __init__(self, config, plan, inputfile, overrides={}, port=9000, extraconfigs=[]):
        app = Flask(__name__)
        self.basedir = os.path.dirname(inputfile) if '/' in inputfile else '.'
        clients = {}
        plans = {}
        for parameterfile in glob("%s/parameters_*.y*ml" % self.basedir):
            search = re.match('.*parameters_(.*)\.(ya?ml)', parameterfile)
            plan_name = search.group(1)
            ext = search.group(2)
            plans[plan_name] = config.client
            if config.client in clients:
                clients[config.client][plan_name] = "%s/parameters_%s.%s" % (self.basedir, plan_name, ext)
            else:
                clients[config.client] = {plan_name: "%s/parameters_%s.%s" % (self.basedir, plan_name, ext)}
        for client in [config.client] + list(config.extraclients.keys()):
            self.parametersfiles = glob("%s/%s/parameters_*.y*ml" % (self.basedir, client))
            for parameterfile in self.parametersfiles:
                search = re.match('.*parameters_(.*)\.(ya?ml)', parameterfile)
                plan_name = search.group(1)
                ext = search.group(2)
                plans[plan_name] = client
                if client in clients:
                    clients[client][plan_name] = "%s/%s/parameters_%s.%s" % (self.basedir, client, plan_name, ext)
                else:
                    clients[client] = {plan_name: "%s/%s/parameters_%s.%s" % (self.basedir, client, plan_name, ext)}
        self.clients = clients if clients else {config.client: {plan: None}}
        self.plans = plans if plans else {plan: config.client}
        self.overrides = overrides

        @app.route('/')
        def index():
            data = {}
            for client in sorted(self.clients):
                data[client] = {}
                for plan_name in sorted(self.clients[client]):
                    current_data = {'vms': []}
                    currentk = config.k if client == config.client else config.extraclients[client]
                    for vm in currentk.list():
                        if vm['plan'] == plan_name:
                            current_data['vms'].append(vm)
                            if 'creationdate' not in current_data and 'creationdate' in vm:
                                current_data['creationdate'] = vm['creationdate']
                            if 'owner' not in current_data and 'owner' in vm:
                                current_data['owner'] = vm['owner']
                    data[client][plan_name] = current_data
            return render_template('index.html', clients=data)

        @app.route("/exposedelete", methods=['POST'])
        def exposedelete():
            """
            delete plan
            """
            if 'name' in request.form:
                plan = request.form['name']
                if plan not in self.plans:
                    return 'Invalid plan name %s' % plan
                elif self.plans[plan] == config.client:
                    currentconfig = self.config
                else:
                    currentconfig = self.extraconfigs[self.plans[plan]]
                result = currentconfig.plan(plan, delete=True)
                response = jsonify(result)
                response.status_code = 200
                return response
            else:
                result = {'result': 'failure', 'reason': "Invalid Data"}
                response = jsonify(result)
                response.status_code = 400

        @app.route("/exposecreate", methods=['POST'])
        def exposecreate():
            """
            create plan
            """
            if 'plan' in request.form:
                plan = request.form['plan']
                if plan not in self.plans:
                    return 'Invalid plan name %s' % plan
                elif self.plans[plan] == config.client:
                    currentconfig = self.config
                    client = config.client
                else:
                    client = self.plans[plan]
                    currentconfig = self.extraconfigs[client]
                parameters = {}
                for p in request.form:
                    if p.startswith('parameter'):
                        value = request.form[p]
                        if value.isdigit():
                            value = int(value)
                        elif value.lower() in ['true', 'false']:
                            value = value.lower() == "true"
                        key = p.replace('parameter_', '')
                        parameters[key] = value
                try:
                    overrides = parameters
                    paramfile = self.clients[client][plan]
                    if paramfile is not None:
                        fileoverrides = get_overrides(paramfile=paramfile)
                        fileoverrides.update(overrides)
                        overrides = fileoverrides
                    if 'mail' in currentconfig.notifymethods and 'mailto' in overrides and overrides['mailto'] != "":
                        newmails = overrides['mailto'].split(',')
                        if currentconfig.mailto:
                            currentconfig.mailto.extend(newmails)
                        else:
                            currentconfig.mailto = newmails
                    if 'owner' in overrides and overrides['owner'] == '':
                        del overrides['owner']
                    currentconfig.plan(plan, delete=True)
                    result = currentconfig.plan(plan, inputfile=inputfile, overrides=overrides)
                except Exception as e:
                    error = 'Hit issue when running plan: %s' % str(e)
                    return render_template('error.html', plan=plan, error=error)
                if result['result'] == 'success':
                    return render_template('success.html', plan=plan)
                else:
                    return render_template('error.html', plan=plan, error=result['reason'])
            else:
                return 'Invalid data'

        @app.route("/exposeform/<string:plan>", methods=['GET'])
        def exposeform(plan):
            """
            form plan
            """
            parameters = self.overrides
            if plan not in self.plans:
                return 'Invalid plan name %s' % plan
            return render_template('form.html', parameters=parameters, plan=plan)

        self.app = app
        self.config = config
        self.extraconfigs = extraconfigs
        self.overrides = overrides
        self.port = port

    def run(self):
        self.app.run(host='0.0.0.0', port=self.port)
