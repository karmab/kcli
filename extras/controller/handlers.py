#!/usr/bin/env python3

import kopf
from kvirt.config import Kconfig
from kvirt import common
import os
from re import sub

DOMAIN = "kcli.karmalabs.local"
VERSION = "v1"


def process_vm(name, namespace, spec, operation='create', timeout=60):
    config = Kconfig(quiet=True)
    exists = config.k.exists(name)
    if operation == "delete" and exists:
        print("Deleting vm %s" % name)
        return config.k.delete(name)
    if operation == "create":
        if not exists:
            profile = spec.get("profile")
            if profile is None:
                if 'image' in spec:
                    profile = spec['image']
                else:
                    profile = name
            print("Creating vm %s" % name)
            if profile is not None:
                result = config.create_vm(name, profile, overrides=dict(spec))
                if result['result'] != 'success':
                    print(result)
                    return result
        info = config.k.info(name)
        image = info.get('image')
        if image is not None and 'ip' not in info:
            raise kopf.TemporaryError("Waiting to populate ip", delay=10)
        return info


def process_plan(plan, spec, operation='create'):
    config = Kconfig(quiet=True)
    if operation == "delete":
        print("Deleting plan %s" % plan)
        return config.plan(plan, delete=True)
    else:
        print("Creating/Updating plan %s" % plan)
        overrides = spec.get('parameters', {})
        workdir = spec.get('workdir', '/workdir')
        inputstring = spec.get('plan')
        if inputstring is None:
            print("Plan %s not created because of missing plan spec" % plan)
            return {'result': 'failure', 'reason': 'missing plan spec'}
        elif os.path.exists("/i_am_a_container"):
            inputstring = sub(r"origin:( *)", r"origin:\1%s/" % workdir, inputstring)
            return config.plan(plan, inputstring=inputstring, overrides=overrides)


def update(name, namespace, diff):
    config = Kconfig(quiet=True)
    k = config.k
    for entry in diff:
        if entry[0] not in ['add', 'change']:
            continue
        arg = entry[1][1]
        value = entry[3]
        if arg == 'plan':
            plan = value
            common.pprint("Updating plan of vm %s to %s..." % (name, plan))
            k.update_metadata(name, 'plan', plan)
        if arg == 'memory':
            memory = value
            common.pprint("Updating memory of vm %s to %s..." % (name, memory))
            k.update_memory(name, memory)
        if arg == 'numcpus':
            numcpus = value
            common.pprint("Updating numcpus of vm %s to %s..." % (name, numcpus))
            k.update_cpus(name, numcpus)
        if arg == 'autostart':
            autostart = value
            common.pprint("Setting autostart for vm %s to %s..." % (name, autostart))
            k.update_start(name, start=autostart)
        if arg == 'information':
            information = value
            common.pprint("Setting information for vm %s..." % name)
            k.update_information(name, information)
        if arg == 'iso':
            iso = value
            common.pprint("Switching iso for vm %s to %s..." % (name, iso))
            k.update_iso(name, iso)
        if arg == 'flavor':
            flavor = value
            common.pprint("Updating flavor of vm %s to %s..." % (name, flavor))
            k.update_flavor(name, flavor)
        if arg == 'start':
            start = value
            if start:
                common.pprint("Starting vm %s..." % name)
                k.start(name)
            else:
                common.pprint("Stopping vm %s..." % name)
                k.stop(name)
        info = config.k.info(name)
        return info


@kopf.on.create(DOMAIN, VERSION, 'vms')
def create_vm(meta, spec, status, namespace, logger, **kwargs):
    operation = 'create'
    name = meta.get('name')
    print("Handling %s on vm %s" % (operation, name))
    return process_vm(name, namespace, spec, operation=operation)


@kopf.on.delete(DOMAIN, VERSION, 'vms')
def delete_vm(meta, spec, namespace, logger, **kwargs):
    operation = 'delete'
    name = meta.get('name')
    print("Handling %s on vm %s" % (operation, name))
    keep = spec.get("keep", False)
    if not keep:
        process_vm(name, namespace, spec, operation=operation)


@kopf.on.update(DOMAIN, VERSION, 'vms')
def update_vm(meta, spec, namespace, old, new, diff, **kwargs):
    operation = 'update'
    name = meta.get('name')
    print("Handling %s on vm %s" % (operation, name))
    return update(name, namespace, diff)


@kopf.on.create(DOMAIN, VERSION, 'plans')
def create_plan(meta, spec, status, namespace, logger, **kwargs):
    operation = 'create'
    name = meta.get('name')
    print("Handling %s on plan %s" % (operation, name))
    return process_plan(name, spec, operation=operation)


@kopf.on.delete(DOMAIN, VERSION, 'plans')
def delete_plan(meta, spec, namespace, logger, **kwargs):
    operation = 'delete'
    name = meta.get('name')
    if spec.get('plan') is not None:
        print("Handling %s on plan %s" % (operation, name))
        process_plan(name, spec, operation=operation)


@kopf.on.update(DOMAIN, VERSION, 'plans')
# def update_plan(meta, spec, namespace, old, new, diff, **kwargs):
def update_plan(meta, spec, status, namespace, logger, **kwargs):
    operation = 'update'
    name = meta.get('name')
    print("Handling %s on vm %s" % (operation, name))
    return process_plan(name, spec, operation=operation)
