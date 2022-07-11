import functools
from kvirt.bottle import Bottle, request, static_file, jinja2_view, response
from glob import glob
from kvirt.common import get_overrides, pprint
import os
import re

basedir = f"{os.path.dirname(Bottle.run.__code__.co_filename)}/expose"
view = functools.partial(jinja2_view, template_lookup=[f"{basedir}/templates"])


class Kexposer():

    def refresh_plans(self, verbose=False):
        plans = []
        owners = {}
        for paramfile in glob(f"{self.basedir}/**/parameters_*.y*ml", recursive=True):
            search = re.match('.*parameters_(.*)\\.ya?ml', paramfile)
            plan = search.group(1)
            try:
                fileoverrides = get_overrides(paramfile=paramfile)
            except:
                continue
            if 'owner' in fileoverrides:
                owners[plan] = fileoverrides['owner']
            plans.append(plan)
            if verbose:
                pprint(f"Adding parameter file {paramfile}")
        self.plans = sorted(plans) if plans else [self.plan]
        self.owners = owners

    def get_client(self, plan, currentconfig, overrides={}):
        matching = glob(f"{self.basedir}/**/parameters_{plan}.y*ml", recursive=True)
        if matching:
            paramfile = matching[0]
            fileoverrides = get_overrides(paramfile=paramfile)
            if 'client' in fileoverrides:
                client = fileoverrides['client']
                currentconfig.__init__(client=client)
                if overrides:
                    fileoverrides.update(overrides)
                    overrides = fileoverrides
        return overrides

    def __init__(self, config, plan, inputfile, overrides={}, port=9000):
        app = Bottle()
        self.basedir = os.path.dirname(inputfile) if '/' in inputfile else '.'
        self.plan = plan
        self.overrides = overrides
        self.refresh_plans(verbose=True)

        @app.route('/static/<filename:path>')
        def server_static(filename):
            return static_file(filename, root=f'{basedir}/static')

        @app.route('/')
        @view('index.html')
        def index():
            self.refresh_plans()
            return {'plans': self.plans, 'owners': self.owners}

        @app.route("/exposedelete", method=['POST'])
        def exposedelete():
            """
            delete plan
            """
            currentconfig = self.config
            if 'plan' in request.forms:
                plan = request.forms['plan']
                if plan not in self.plans:
                    return f'Invalid plan name {plan}'
                self.get_client(plan, currentconfig)
                result = currentconfig.delete_plan(plan)
                response.status = 200
            else:
                result = {'result': 'failure', 'reason': "Missing plan in data"}
                response.status = 400
            return result

        @app.route("/exposecreate", method='POST')
        @view('result.html')
        def exposecreate():
            """
            create plan
            """
            currentconfig = self.config
            if 'plan' in request.forms:
                plan = request.forms['plan']
                if plan not in self.plans:
                    return f'Invalid plan name {plan}'
                parameters = {}
                for p in request.forms:
                    if p.startswith('parameter'):
                        value = request.forms[p]
                        if value.isdigit():
                            value = int(value)
                        elif value.lower() in ['true', 'false']:
                            value = value.lower() == "true"
                        key = p.replace('parameter_', '')
                        parameters[key] = value
                try:
                    overrides = self.get_client(plan, currentconfig, overrides=parameters)
                    if 'mail' in currentconfig.notifymethods and 'mail_to' in overrides and overrides['mail_to'] != "":
                        newmails = overrides['mail_to'].split(',')
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
                    result = {'result': 'failure', 'error': error}
                return {'plan': plan, 'result': result}
            else:
                return 'Missing plan in data'

        @app.route("/exposeform/<plan>")
        @view('form.html')
        def exposeform(plan):
            """
            form plan
            """
            parameters = self.overrides
            if plan not in self.plans:
                return f'Invalid plan name {plan}'
            return {'parameters': parameters, 'plan': plan}

        @app.route("/infoplan/<plan>")
        @view('infoplan.html')
        def infoplan(plan):
            """
            info plan
            """
            currentconfig = self.config
            if plan not in self.plans:
                return f'Invalid plan name {plan}'
            self.get_client(plan, currentconfig)
            vms = currentconfig.info_specific_plan(plan)
            creationdate = ''
            owner = self.owners[plan] if plan in self.owners else ''
            if vms:
                creationdate = vms[0].get('creationdate', creationdate)
                if 'owner' in vms[0]:
                    owner = vms[0]['owner']
                return {'vms': vms, 'plan': plan, 'client': currentconfig.client, 'creationdate': creationdate,
                        'owner': owner}

        self.app = app
        self.config = config
        self.overrides = overrides
        self.port = port

    def run(self):
        self.app.run(host='0.0.0.0', port=self.port)
