from kvirt.config import Kconfig
from flask import Flask
from flask import render_template
from glob import glob
import os
import re

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
    config = Kconfig()
    plans = {plan: [] for plan in plans}
    for vm in config.k.list():
        if vm['plan'] in plans:
            plans[vm['plan']].append(vm)
    return render_template('main.html', plans=plans)

# app.run(host='0.0.0.0', port=9000)
