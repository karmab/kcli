from flask import Flask
from flask import render_template, request, jsonify
from glob import glob
import os
import re


class Kexposer():
    def __init__(self, config, inputfile, overrides={}):
        app = Flask(__name__)

        @app.route('/')
        def main():
            parametersfiles = glob("parameters_*.yml")
            if parametersfiles:
                plans = []
                for parameterfile in parametersfiles:
                    search = re.match('parameters_(.*)\.ya?ml', parameterfile)
                    plans.append(search.group(1))
            else:
                if 'PLAN' in os.environ:
                    plans = [os.environ['PLAN']]
                else:
                    return 'Plan needs to be defined for the service to work.\
                        Define it as an env variable or create parameters files'
            plans = {plan: [] for plan in plans}
            for vm in config.k.list():
                if vm['plan'] in plans:
                    plans[vm['plan']].append(vm)
            finalplans = []
            for plan in plans:
                finalplans.append({'name': plan, 'vms': plans[plan]})
            return render_template('main.html', plans=sorted(finalplans, key=lambda p: p['name']))

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
            delete plan
            """
            if 'name' in request.form:
                plan = request.form['name']
                overrides = request.form['overrides'] if 'overrides' in request.form else {}
                result = config.plan(plan, inputfile=inputfile, overrides=overrides)
                response = jsonify(result)
                response.status_code = 200
                return response
            else:
                result = {'result': 'failure', 'reason': "Invalid Data"}
                response = jsonify(result)
                response.status_code = 400
        self.app = app
        self.config = config
        self.overrides = overrides

    def run(self):
        self.app.run(host='0.0.0.0', port=9000)
