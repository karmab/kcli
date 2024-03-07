import functools
from kvirt.bottle import Bottle, request, static_file, jinja2_view, response
from glob import glob
from kvirt.common import get_overrides, pprint, get_parameters
import os
import re
import yaml


def convert_value(value):
    if value.isdigit():
        value = int(value)
    elif value.lower() in ['true', 'false']:
        value = value.lower() == "true"
    return value


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

    def __init__(self, config, plan, inputfile, overrides={}, port=9000, pfmode=False, cluster=False, extras=False):
        app = Bottle()
        basedir = f"{os.path.dirname(Bottle.run.__code__.co_filename)}/expose"
        view = functools.partial(jinja2_view, template_lookup=[f"{basedir}/templates"])
        self.basedir = os.path.dirname(inputfile) if '/' in inputfile else '.'
        self.plan = plan
        self.overrides = overrides
        self.pfmode = pfmode
        self.extras = extras
        self.cluster = cluster
        self.refresh_plans(verbose=True)
        self.inputfile = inputfile

        @app.route('/static/<filename:path>')
        def server_static(filename):
            return static_file(filename, root=f'{basedir}/static')

        @app.route('/')
        @view('index.html')
        def index():
            self.refresh_plans()
            return {'plans': self.plans, 'owners': self.owners}

        @app.route('/planstable')
        @view('planstable.html')
        def plansstable():
            self.refresh_plans()
            return {'plans': self.plans, 'owners': self.owners}

        @app.route("/exposecreate", method='POST')
        @view('result.html')
        def exposecreateweb():
            update = False
            currentconfig = self.config
            if 'plan' in request.forms:
                plan = request.forms['plan']
                if plan not in self.plans:
                    return f'Invalid plan name {plan}'
                pfdata = None
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
                    elif p == 'update':
                        update = True
                    elif p == 'pf':
                        pfdata = request.forms[p]
                if pfdata is not None:
                    try:
                        new_parameters = yaml.safe_load(pfdata)
                    except:
                        new_parameters = {}
                    new_parameters.update(parameters)
                    parameters = new_parameters
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
                    inputfile = overrides.get('inputfile', self.inputfile)
                    if update:
                        result = currentconfig.plan(plan, inputfile=inputfile, overrides=overrides, update=True)
                    else:
                        if self.cluster:
                            currentconfig.delete_kube(plan)
                        else:
                            currentconfig.delete_plan(plan)
                        result = currentconfig.plan(plan, inputfile=inputfile, overrides=overrides)
                except Exception as e:
                    error = f'Hit issue when running plan: {str(e)}'
                    response.status = 400
                    result = {'result': 'failure', 'error': error}
                result.update({'plan': plan})
                return result
            else:
                return 'Missing plan in data'

        @app.route("/exposeform/<plan>")
        @view('form.html')
        def exposeform(plan):
            parameters = self.overrides
            if plan not in self.plans:
                return f'Invalid plan name {plan}'
            inputfile = self.overrides.get('inputfile', self.inputfile)
            info = get_parameters(inputfile, planfile=True)
            info = info.get('info', 'N/A')
            return {'parameters': parameters, 'plan': plan, 'pfmode': self.pfmode, 'info': info, 'extras': self.extras}

        def _infoplan(plan):
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

        def _infocluster(plan):
            currentconfig = self.config
            data = currentconfig.info_specific_kube(plan)
            data['kube'] = plan
            return data

        @app.route("/infoplan/<plan>")
        @view('infoplan.html')
        def infoplan(plan):
            if self.cluster:
                return _infocluster(plan)
            else:
                return _infoplan(plan)

        # API

        @app.route('/expose')
        def exposelist():
            return {'plans': self.plans, 'owners': self.owners, 'overrides': self.overrides}

        @app.route("/expose", method='POST')
        def exposeplancreate():
            update = False
            currentconfig = self.config
            json = request.json
            if json is None:
                response.status = 400
                return 'Invalid json'
            if 'plan' in json:
                plan = json['plan']
                if plan not in self.plans:
                    response.status = 400
                    return f'Invalid plan name {plan}'
                pfdata = None
                parameters = {}
                for p in json:
                    value = request.json[p]
                    if p == 'extras':
                        extra_parameters = {}
                        for entry in value.strip().split('-P '):
                            if entry != '':
                                new_param, new_value = entry.split('=')
                                extra_parameters[new_param] = convert_value(new_value)
                        parameters.update(extra_parameters)
                    elif p not in self.overrides:
                        print(f"Skipping parameter {p}")
                        continue
                    parameters[p] = convert_value(new_value)
                if pfdata is not None:
                    try:
                        new_parameters = yaml.safe_load(pfdata)
                    except:
                        new_parameters = {}
                    new_parameters.update(parameters)
                    parameters = new_parameters
                print(parameters)
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
                    inputfile = self.overrides.get('inputfile', self.inputfile)
                    if update:
                        result = currentconfig.plan(plan, inputfile=inputfile, overrides=overrides, update=True)
                    else:
                        if self.cluster:
                            currentconfig.delete_kube(plan)
                        else:
                            currentconfig.delete_plan(plan)
                        result = currentconfig.plan(plan, inputfile=inputfile, overrides=overrides)
                except Exception as e:
                    error = f'Hit issue when running plan: {str(e)}'
                    response.status = 400
                    result = {'result': 'failure', 'error': error}
                return {'plan': plan, 'result': result}
            else:
                return 'Missing plan in data'

        @app.route("/expose/<plan>")
        def exposeplaninfo(plan):
            if self.cluster:
                return _infocluster(plan)
            else:
                return _infoplan(plan)

        @app.route('/expose/kubeconfig/kubeconfig.<kube>')
        def kubeconfigfile(kube):
            kubeconfig = os.path.expanduser(f'~/.kcli/clusters/{kube}/auth/kubeconfig')
            if self.cluster and os.path.exists(kubeconfig):
                return static_file('kubeconfig', root=os.path.dirname(kubeconfig), mimetype='application/octet-stream')
            else:
                response.status = 404
                return {}

        @app.route('/expose/<kube>/kubeconfig')
        def kubeconfig(kube):
            kubeconfig = os.path.expanduser(f'~/.kcli/clusters/{kube}/auth/kubeconfig')
            if self.cluster and os.path.exists(kubeconfig):
                return open(kubeconfig).read()
            else:
                response.status = 404
                return {}

        @app.route("/expose/<plan>", method=['DELETE'])
        def exposedelete(plan):
            currentconfig = self.config
            if plan not in self.plans:
                response.status = 400
                return f'Invalid plan name {plan}'
            self.get_client(plan, currentconfig)
            if self.cluster:
                result = currentconfig.delete_kube(plan)
            else:
                result = currentconfig.delete_plan(plan)
            response.status = 200
            return result

        self.app = app
        self.config = config
        self.overrides = overrides
        self.port = port

    def run(self):
        self.app.run(host='0.0.0.0', port=self.port)
