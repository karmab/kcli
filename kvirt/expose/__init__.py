from flask import Flask
from flask import render_template, request, jsonify
from glob import glob
from kvirt.common import pprint, get_overrides
import os
import re


class Kexposer():
    def __init__(self, config, inputfile, overrides={}):
        app = Flask(__name__)
        self.parametersfiles = glob("parameters_*.yml")
        if self.parametersfiles:
            plans = []
            for parameterfile in self.parametersfiles:
                search = re.match('parameters_(.*)\.ya?ml', parameterfile)
                plans.append(search.group(1))
        else:
            if 'PLAN' in os.environ:
                plans = [os.environ['PLAN']]
            else:
                pprint('Plan needs to be defined for the service to work.\
                              Define it as an env variable or create parameters files', color='red')
                os._exit(1)
        self.plans = plans
        self.overrides = overrides

        @app.route('/')
        def index():
            creationdate = ""
            plans = {plan: [] for plan in self.plans}
            for vm in config.k.list():
                if vm['plan'] in plans:
                    if creationdate == "":
                        creationdate = vm['creationdate']
                        print(creationdate)
                    plans[vm['plan']].append(vm)
            finalplans = []
            for plan in plans:
                finalplans.append({'name': plan, 'vms': plans[plan]})
            return render_template('list.html', plans=sorted(finalplans, key=lambda p: p['name']),
                                   creationdate=creationdate)

        @app.route("/exposedelete", methods=['POST'])
        def exposedelete():
            """
            delete plan
            """
            if 'name' in request.form:
                plan = request.form['name']
                result = self.config.plan(plan, delete=True)
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
                parameters = {}
                for p in request.form:
                    if p.startswith('parameter'):
                        value = request.form[p]
                        if value.isdigit():
                            value = int(value)
                        key = p.replace('parameter_', '')
                        parameters[key] = value
                try:
                    overrides = parameters
                    if "parameters_%s.yml" % plan in self.parametersfiles:
                        fileoverrides = get_overrides(paramfile="parameters_%s.yml" % plan)
                        overrides.update(fileoverrides)
                    if 'mail' in config.notifymethods and 'mailto' in overrides and overrides['mailto'] != "":
                        newmails = overrides['mailto'].split(',')
                        if config.mailto:
                            config.mailto.extend(newmails)
                        else:
                            config.mailto = newmails
                    result = config.plan(plan, inputfile=inputfile, overrides=overrides)
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
        self.overrides = overrides

    def run(self):
        self.app.run(host='0.0.0.0', port=9000)
