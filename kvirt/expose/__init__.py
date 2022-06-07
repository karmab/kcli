from flask import Flask
from flask import render_template, request, jsonify
from glob import glob
from kvirt.common import get_overrides, pprint
import os
import re


class Kexposer():

    def refresh_plans(self):
        plans = []
        owners = {}
        for paramfile in glob(f"{self.basedir}/**/parameters_*.y*ml", recursive=True):
            search = re.match('.*parameters_(.*)\\.ya?ml', paramfile)
            plan = search.group(1)
            pprint(f"Adding parameter file {paramfile}")
            plans.append(plan)
            fileoverrides = get_overrides(paramfile=paramfile)
            if 'owner' in fileoverrides:
                owners[plan] = fileoverrides['owner']
        self.plans = sorted(plans) if plans else [plan]
        self.owners = owners

    def __init__(self, config, plan, inputfile, overrides={}, port=9000):
        app = Flask(__name__)
        self.basedir = os.path.dirname(inputfile) if '/' in inputfile else '.'
        self.overrides = overrides
        self.refresh_plans()

        @app.route('/')
        def index():
            self.refresh_plans()
            return render_template('index.html', plans=self.plans, owners=self.owners)

        @app.route("/exposedelete", methods=['POST'])
        def exposedelete():
            """
            delete plan
            """
            currentconfig = self.config
            if 'name' in request.form:
                plan = request.form['name']
                if plan not in self.plans:
                    return f'Invalid plan name {plan}'
                matching = glob(f"{self.basedir}/**/parameters_{plan}.y*ml", recursive=True)
                if matching:
                    paramfile = matching[0]
                    fileoverrides = get_overrides(paramfile=paramfile)
                    if 'client' in fileoverrides:
                        client = fileoverrides['client']
                        currentconfig.__init__(client=client)
                result = currentconfig.delete_plan(plan)
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
            currentconfig = self.config
            if 'plan' in request.form:
                plan = request.form['plan']
                if plan not in self.plans:
                    return f'Invalid plan name {plan}'
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
                    matching = glob(f"{self.basedir}/**/parameters_{plan}.y*ml", recursive=True)
                    if matching:
                        paramfile = matching[0]
                        fileoverrides = get_overrides(paramfile=paramfile)
                        if 'client' in fileoverrides:
                            client = fileoverrides['client']
                            currentconfig.__init__(client=client)
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
                    currentconfig.delete_plan(plan)
                    result = currentconfig.plan(plan, inputfile=inputfile, overrides=overrides)
                except Exception as e:
                    error = f'Hit issue when running plan: {str(e)}'
                    return render_template('error.html', plan=plan, error=error)
                if result['result'] == 'success':
                    return render_template('success.html', plan=plan)
                else:
                    return render_template('error.html', plan=plan, failedvms=result['failedvms'])
            else:
                return 'Invalid data'

        @app.route("/exposeform/<string:plan>", methods=['GET'])
        def exposeform(plan):
            """
            form plan
            """
            parameters = self.overrides
            if plan not in self.plans:
                return f'Invalid plan name {plan}'
            return render_template('form.html', parameters=parameters, plan=plan)

        @app.route("/infoplan/<string:plan>", methods=['GET'])
        def infoplan(plan):
            """
            info plan
            """
            currentconfig = self.config
            client = currentconfig.client
            if plan not in self.plans:
                return f'Invalid plan name {plan}'
            matching = glob(f"{self.basedir}/**/parameters_{plan}.y*ml", recursive=True)
            if matching:
                paramfile = matching[0]
                fileoverrides = get_overrides(paramfile=paramfile)
                if 'client' in fileoverrides:
                    client = fileoverrides['client']
                    currentconfig.__init__(client=client)
            vms = currentconfig.info_specific_plan(plan)
            creationdate = ''
            owner = self.owners[plan] if plan in self.owners else ''
            if vms:
                creationdate = vms[0].get('creationdate', creationdate)
                if 'owner' in vms[0]:
                    owner = vms[0]['owner']
            return render_template('infoplan.html', vms=vms, plan=plan, client=client, creationdate=creationdate,
                                   owner=owner)

        self.app = app
        self.config = config
        self.overrides = overrides
        self.port = port

    def run(self):
        self.app.run(host='0.0.0.0', port=self.port)
