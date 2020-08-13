from flask import Flask
from flask import render_template, request, jsonify
from glob import glob
from kvirt.common import pprint, get_overrides
import os
import re


class Kexposer():
    def __init__(self, config, inputfile, overrides={}, plan=None, port=9000):
        app = Flask(__name__)
        self.basedir = os.path.dirname(inputfile) if '/' in inputfile else '.'
        self.parametersfiles = glob("%s/parameters_*.y*ml" % self.basedir)
        if self.parametersfiles:
            plans = []
            for parameterfile in self.parametersfiles:
                search = re.match('.*parameters_(.*)\.y*ml', parameterfile)
                plans.append(search.group(1))
        elif plan is not None:
            plans = [plan]
        else:
            if 'PLAN' in os.environ:
                plans = [os.environ['PLAN']]
            else:
                msg = 'Define plan as an env variable or create parameters files'
                pprint(msg, color='red')
                os._exit(1)
        self.plans = plans
        self.overrides = overrides

        @app.route('/')
        def index():
            creationdates = {}
            plans = {plan: [] for plan in self.plans}
            planowners = {}
            for vm in config.k.list():
                if vm['plan'] in plans:
                    if vm['plan'] not in creationdates:
                        creationdates[vm['plan']] = vm['creationdate']
                    plans[vm['plan']].append(vm)
                    if 'owner' in vm and vm['plan'] not in planowners:
                        planowners[vm['plan']] = vm['owner']
            finalplans = []
            for plan in plans:
                finalplans.append({'name': plan, 'vms': plans[plan]})
            return render_template('list.html', plans=sorted(finalplans, key=lambda p: p['name']),
                                   planowners=planowners, creationdates=creationdates)

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
                    if self.parametersfiles:
                        for paramfile in self.parametersfiles:
                            if paramfile.startswith("%s/parameters_%s" % (self.basedir, plan)):
                                fileoverrides = get_overrides(paramfile=paramfile)
                                fileoverrides.update(overrides)
                        overrides = fileoverrides
                    if 'mail' in config.notifymethods and 'mailto' in overrides and overrides['mailto'] != "":
                        newmails = overrides['mailto'].split(',')
                        if config.mailto:
                            config.mailto.extend(newmails)
                        else:
                            config.mailto = newmails
                    if 'owner' in overrides and overrides['owner'] == '':
                        del overrides['owner']
                    config.plan(plan, delete=True)
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
        self.port = port

    def run(self):
        self.app.run(host='0.0.0.0', port=self.port)
