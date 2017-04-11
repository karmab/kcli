#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
docker utilites
"""

import docker
import os


def create_container(self, name, image, nets=None, cmd=None, ports=[], volumes=[], environment=[], label=None):
    if self.host == '127.0.0.1':
        finalvolumes = {}
        if volumes is not None:
            for i, volume in enumerate(volumes):
                if isinstance(volume, str):
                    if len(volume.split(':')) == 2:
                        origin, destination = volume.split(':')
                        finalvolumes[origin] = {'bind': destination, 'mode': 'rw'}
                    else:
                        finalvolumes[volume] = {'bind': volume, 'mode': 'rw'}
                elif isinstance(volume, dict):
                    path = volume.get('path')
                    origin = volume.get('origin')
                    destination = volume.get('destination')
                    mode = volume.get('mode', 'rw')
                    if origin is None or destination is None:
                        if path is None:
                            continue
                        finalvolumes[origin] = {'bind': path, 'mode': mode}
                    else:
                        finalvolumes[origin] = {'bind': destination, 'mode': mode}
        if ports is not None:
            ports = {'%s/tcp' % k: k for k in ports}
        if label is not None and isinstance(label, str) and len(label.split('=')) == 2:
            key, value = label.split('=')
            labels = {key: value}
        else:
            labels = None
        base_url = 'unix://var/run/docker.sock'
        finalenv = {}
        if environment is not None:
            for env in enumerate(environment):
                if isinstance(env, str):
                    if len(env.split(':')) == 2:
                        key, value = env.split(':')
                        finalenv[key] = value
                    else:
                        continue
                elif isinstance(env, dict):
                    if len(env.keys()) == 1:
                        key = env.keys[0]
                        value = env[key]
                        finalenv[key] = value
                    else:
                        continue

        d = docker.DockerClient(base_url=base_url, version='1.22')
        # d.containers.run(image, name=name, command=cmd, networks=nets, detach=True, ports=ports)
        d.containers.run(image, name=name, command=cmd, detach=True, ports=ports, volumes=finalvolumes, stdin_open=True, tty=True, labels=labels, environment=finalenv)
    else:
        # netinfo = ''
        # for net in nets:
        #    netinfo = "%s --net=%s" % (netinfo, net)
        portinfo = ''
        if ports is not None:
            for port in ports:
                if isinstance(port, int):
                    oriport = port
                    destport = port
                elif isinstance(port, str):
                    if len(port.split(':')) == 2:
                        oriport, destport = port.split(':')
                    else:
                        oriport = port
                        destport = port
                elif isinstance(port, dict) and 'origin' in port and 'destination' in port:
                    oriport = port['origin']
                    destport = port['destination']
                else:
                    continue
                portinfo = "%s -p %s:%s" % (portinfo, oriport, destport)
        volumeinfo = ''
        if volumes is not None:
            for volume in volumes:
                if isinstance(volume, str):
                    if len(volume.split(':')) == 2:
                        origin, destination = volume.split(':')
                    else:
                        origin = volume
                        destination = volume
                elif isinstance(volume, dict):
                    path = volume.get('path')
                    origin = volume.get('origin')
                    destination = volume.get('destination')
                    if origin is None or destination is None:
                        if path is None:
                            continue
                        origin = path
                        destination = path
                volumeinfo = "%s -v %s:%s" % (volumeinfo, origin, destination)
        envinfo = ''
        if environment is not None:
            for env in environment:
                if isinstance(env, str):
                    if len(env.split(':')) == 2:
                        key, value = env.split(':')
                    else:
                        continue
                elif isinstance(env, dict):
                    if len(env.keys()) == 1:
                        key = env.keys()[0]
                        value = env[key]
                    else:
                        continue
                envinfo = "%s -e %s=%s" % (envinfo, key, value)
        dockercommand = "docker run -it %s %s %s --name %s -l %s -d %s" % (volumeinfo, envinfo, portinfo, name, label, image)
        if cmd is not None:
            dockercommand = "%s %s" % (dockercommand, cmd)
        command = "ssh -p %s %s@%s %s" % (self.port, self.user, self.host, dockercommand)
        os.system(command)
    return {'result': 'success'}


def delete_container(self, name):
    if self.host == '127.0.0.1':
        base_url = 'unix://var/run/docker.sock'
        d = docker.DockerClient(base_url=base_url, version='1.22')
        containers = [container for container in d.containers.list() if container.name == name]
        if containers:
            for container in containers:
                container.remove(force=True)
    else:
        dockercommand = "docker rm -f %s" % name
        command = "ssh -p %s %s@%s %s" % (self.port, self.user, self.host, dockercommand)
        os.system(command)
    return {'result': 'success'}


def start_container(self, name):
    if self.host == '127.0.0.1':
        base_url = 'unix://var/run/docker.sock'
        d = docker.DockerClient(base_url=base_url, version='1.22')
        containers = [container for container in d.containers.list(all=True) if container.name == name]
        if containers:
            for container in containers:
                container.start()
    else:
        dockercommand = "docker start %s" % name
        command = "ssh -p %s %s@%s %s" % (self.port, self.user, self.host, dockercommand)
        os.system(command)
    return {'result': 'success'}


def stop_container(self, name):
    if self.host == '127.0.0.1':
        base_url = 'unix://var/run/docker.sock'
        d = docker.DockerClient(base_url=base_url, version='1.22')
        containers = [container for container in d.containers.list() if container.name == name]
        if containers:
            for container in containers:
                container.stop()
    else:
        dockercommand = "docker stop %s" % name
        command = "ssh -p %s %s@%s %s" % (self.port, self.user, self.host, dockercommand)
        os.system(command)
    return {'result': 'success'}


def console_container(self, name):
    if self.host == '127.0.0.1':
        # base_url = 'unix://var/run/docker.sock'
        dockercommand = "docker attach %s" % name
        os.system(dockercommand)
        # d = docker.DockerClient(base_url=base_url)
        # containers = [container.id for container in d.containers.list() if container.name == name]
        # if containers:
        #    for container in containers:
        #        container.attach()
    else:
        dockercommand = "docker attach %s" % name
        command = "ssh -t -p %s %s@%s %s" % (self.port, self.user, self.host, dockercommand)
        os.system(command)
    return {'result': 'success'}


def list_containers(self):
    containers = []
    if self.host == '127.0.0.1':
        base_url = 'unix://var/run/docker.sock'
        d = docker.DockerClient(base_url=base_url, version='1.22')
        # containers = [container.name for container in d.containers.list()]
        for container in d.containers.list(all=True):
            name = container.name
            state = container.status
            state = state.split(' ')[0]
            if state.startswith('running'):
                state = 'up'
            else:
                state = 'down'
            source = container.attrs['Config']['Image']
            labels = container.attrs['Config']['Labels']
            if 'plan' in labels:
                plan = labels['plan']
            else:
                plan = ''
            command = container.attrs['Config']['Cmd']
            if command is None:
                command = ''
            else:
                command = command[0]
            ports = container.attrs['NetworkSettings']['Ports']
            if ports:
                portinfo = []
                for port in ports:
                    if ports[port] is None:
                        newport = port
                    else:
                        hostport = ports[port][0]['HostPort']
                        hostip = ports[port][0]['HostIp']
                        newport = "%s:%s->%s" % (hostip, hostport, port)
                    portinfo.append(newport)
                portinfo = ','.join(portinfo)
            else:
                portinfo = ''
            containers.append([name, state, source, plan, command, portinfo])
    else:
        containers = []
        # dockercommand = "docker ps --format '{{.Names}}'"
        dockercommand = "docker ps -a --format \"'{{.Names}}?{{.Status}}?{{.Image}}?{{.Command}}?{{.Ports}}?{{.Label \\\"plan\\\"}}'\""
        command = "ssh -p %s %s@%s %s" % (self.port, self.user, self.host, dockercommand)
        results = os.popen(command).readlines()
        for container in results:
            #    containers.append(container.strip())
            name, state, source, command, ports, plan = container.split('?')
            if state.startswith('Up'):
                state = 'up'
            else:
                state = 'down'
            # labels = {i.split('=')[0]: i.split('=')[1] for i in labels.split(',')}
            # if 'plan' in labels:
            #    plan = labels['plan']
            # else:
            #     plan = ''
            command = command.strip().replace('"', '')
            containers.append([name, state, source, plan, command, ports])
    return containers


def exists_container(self, name):
    if self.host == '127.0.0.1':
        base_url = 'unix://var/run/docker.sock'
        d = docker.DockerClient(base_url=base_url, version='1.22')
        containers = [container.id for container in d.containers.list(all=True) if container.name == name]
        if containers:
            return True
    else:
        dockercommand = "docker ps -a --format '{{.Names}}'"
        command = "ssh -p %s %s@%s %s" % (self.port, self.user, self.host, dockercommand)
        results = os.popen(command).readlines()
        for container in results:
            containername = container.strip()
            if containername == name:
                return True
    return False
