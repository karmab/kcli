#!/usr/bin/env python3

from kubernetes import client, watch
import kopf
from kvirt.config import Kconfig
from kvirt.common import pprint, error
import os
from re import sub
import threading

DOMAIN = "kcli.karmalabs.local"
VERSION = "v1"


def watch_configmaps():
    v1 = client.CoreV1Api()
    namespace = 'kcli-infra'
    config_maps = ['kcli-conf', 'kcli-ssh']
    while True:
        stream = watch.Watch().stream(v1.list_namespaced_config_map, namespace, timeout_seconds=10)
        for event in stream:
            obj = event["object"]
            obj_dict = obj.to_dict()
            current_config_map_name = obj_dict['metadata']['name']
            if current_config_map_name in config_maps and event["type"] == 'MODIFIED':
                print("Exiting as configmap was changed")
                os._exit(1)


def process_vm(name, namespace, spec, operation='create', timeout=60):
    config = Kconfig(quiet=True)
    exists = config.k.exists(name)
    if operation == "delete" and exists:
        pprint(f"Deleting vm {name}")
        return config.k.delete(name)
    if operation == "create":
        if not exists:
            profile = spec.get("profile")
            if profile is None:
                if 'image' in spec:
                    profile = spec['image']
                else:
                    profile = name
            pprint(f"Creating vm {name}")
            if profile is not None:
                result = config.create_vm(name, profile, overrides=dict(spec))
                if result['result'] != 'success':
                    return result
        info = config.k.info(name)
        image = info.get('image')
        if image is not None and 'ip' not in info:
            raise kopf.TemporaryError("Waiting to populate ip", delay=10)
        return info


def process_plan(plan, spec, operation='create'):
    config = Kconfig(quiet=True)
    if operation == "delete":
        pprint(f"Deleting plan {plan}")
        return config.delete_plan(plan)
    else:
        pprint(f"Creating/Updating plan {plan}")
        overrides = spec.get('parameters', {})
        workdir = spec.get('workdir', '/workdir')
        inputstring = spec.get('plan')
        if inputstring is None:
            error("Plan %s not created because of missing plan spec" % plan)
            return {'result': 'failure', 'reason': 'missing plan spec'}
        else:
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
            pprint(f"Updating plan of vm {name} to {plan}...")
            k.update_metadata(name, 'plan', plan)
        if arg == 'memory':
            memory = value
            pprint(f"Updating memory of vm {name} to {memory}...")
            k.update_memory(name, memory)
        if arg == 'numcpus':
            numcpus = value
            pprint(f"Updating numcpus of vm {name} to {numcpus}...")
            k.update_cpus(name, numcpus)
        if arg == 'autostart':
            autostart = value
            pprint(f"Setting autostart for vm {name} to {autostart}...")
            k.update_start(name, start=autostart)
        if arg == 'information':
            information = value
            pprint(f"Setting information for vm {name}...")
            k.update_information(name, information)
        if arg == 'iso':
            iso = value
            pprint(f"Switching iso for vm {name} to {iso}...")
            k.update_iso(name, iso)
        if arg == 'flavor':
            flavor = value
            pprint(f"Updating flavor of vm {name} to {flavor}...")
            k.update_flavor(name, flavor)
        if arg == 'start':
            start = value
            if start:
                pprint(f"Starting vm {name}...")
                k.start(name)
            else:
                pprint(f"Stopping vm {name}...")
                k.stop(name)
        info = config.k.info(name)
        return info


@kopf.on.resume(DOMAIN, VERSION, 'vms')
def handle_configmaps(spec, **_):
    threading.Thread(target=watch_configmaps).start()


@kopf.on.create(DOMAIN, VERSION, 'vms')
def create_vm(meta, spec, status, namespace, logger, **kwargs):
    operation = 'create'
    name = meta.get('name')
    pprint(f"Handling {operation} on vm {name}")
    return process_vm(name, namespace, spec, operation=operation)


@kopf.on.delete(DOMAIN, VERSION, 'vms')
def delete_vm(meta, spec, namespace, logger, **kwargs):
    operation = 'delete'
    name = meta.get('name')
    pprint(f"Handling {operation} on vm {name}")
    keep = spec.get("keep", False)
    if not keep:
        process_vm(name, namespace, spec, operation=operation)


@kopf.on.update(DOMAIN, VERSION, 'vms')
def update_vm(meta, spec, namespace, old, new, diff, **kwargs):
    operation = 'update'
    name = meta.get('name')
    pprint(f"Handling {operation} on vm {name}")
    return update(name, namespace, diff)


@kopf.on.create(DOMAIN, VERSION, 'plans')
def create_plan(meta, spec, status, namespace, logger, **kwargs):
    operation = 'create'
    name = meta.get('name')
    pprint(f"Handling {operation} on plan {name}")
    return process_plan(name, spec, operation=operation)


@kopf.on.delete(DOMAIN, VERSION, 'plans')
def delete_plan(meta, spec, namespace, logger, **kwargs):
    operation = 'delete'
    name = meta.get('name')
    if spec.get('plan') is not None:
        pprint(f"Handling {operation} on plan {name}")
        process_plan(name, spec, operation=operation)


@kopf.on.update(DOMAIN, VERSION, 'plans')
def update_plan(meta, spec, status, namespace, logger, **kwargs):
    operation = 'update'
    name = meta.get('name')
    pprint(f"Handling {operation} on vm {name}")
    return process_plan(name, spec, operation=operation)
