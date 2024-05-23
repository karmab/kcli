# -*- coding: utf-8 -*-

import os
from shutil import which


class Kcontainer():
    def __init__(self, host='127.0.0.1', user='root', port=22, engine='podman', debug=False, insecure=False):
        self.host = host
        self.user = user
        self.port = port
        self.debug = debug
        self.containermode = False
        self.engine = engine
        self.insecure = insecure
        if self.host == '127.0.0.1' and which(engine) is None:
            reason = f"executable {engine} not found in path"
            return {'result': 'failure', 'reason': reason}
        self.engine = engine
        if self.host == '127.0.0.1' and os.path.exists("/i_am_a_container"):
            self.containermode = True
            if self.engine == 'podman':
                if not os.path.exists("/run/podman/io.podman"):
                    reason = "You need to add -v /run/podman/io.podman:/run/podman/io.podman to container alias"
                    return {'result': 'failure', 'reason': reason}
                from podman import Client as podmanclient
                self.d = podmanclient(uri='unix:/run/podman/io.podman')
            else:
                if not os.path.exists("/var/run/docker.sock"):
                    reason = "You need to add -v /var/run/docker.sock:/var/run/docker.sock to container alias"
                    return {'result': 'failure', 'reason': reason}
                from docker import DockerClient as dockerclient
                self.d = dockerclient(base_url='unix://var/run/docker.sock', version='1.22')

    def create_container(self, name, image, nets=None, cmds=[], ports=[], volumes=[], environment=[], label=None,
                         overrides={}):
        engine = self.engine
        if self.containermode:
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
                labels = {'plan': 'kvirt'}
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
                        if len(list(env)) == 1:
                            key = env.keys[0]
                            value = env[key]
                            finalenv[key] = value
                        else:
                            continue
            if ':' not in image:
                image = '%s:latest' % image
            cmd = ';'.join(cmds) if cmds else None
            self.d.containers.run(image, name=name, command=cmd, detach=True, ports=ports, volumes=finalvolumes,
                                  stdin_open=True, tty=True, labels=labels, environment=finalenv, stdout=True)
        else:
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
                        if len(list(env)) == 1:
                            key = list(env)[0]
                            value = env[key]
                        else:
                            continue
                    envinfo = "%s -e %s=%s" % (envinfo, key, value)
            labelcmd = '-l plan=kvirt'
            if 'labels' in overrides:
                labels = overrides['labels']
                labelcmd = ' '.join('-l %s=%s' % (label.split('=')[0], label.split('=')[1]) for label in labels)
            selinux = "--security-opt label=disable" if self.insecure else ""
            runcommand = "%s run %s -it %s %s %s --name %s %s -d %s" % (engine, selinux, volumeinfo, envinfo, portinfo,
                                                                        name, labelcmd, image)
            if cmds:
                runcommand = '%s sh -c \\"%s\\"' % (runcommand, ';'.join(cmds))
            if self.host != '127.0.0.1':
                runcommand = 'ssh -p %s %s@%s "%s"' % (self.port, self.user, self.host, runcommand)
            if self.debug:
                print(runcommand)
            os.system(runcommand)
        return {'result': 'success'}

    def delete_container(self, name):
        engine = self.engine
        if self.containermode:
            containers = [container for container in self.d.containers.list() if container.name == name]
            if containers:
                for container in containers:
                    container.remove(force=True)
        else:
            rmcommand = "%s rm -f %s" % (engine, name)
            if self.host != '127.0.0.1':
                rmcommand = "ssh -p %s %s@%s %s" % (self.port, self.user, self.host, rmcommand)
            os.system(rmcommand)
        return {'result': 'success'}

    def start_container(self, name):
        engine = self.engine
        if self.containermode:
            containers = [container for container in self.d.containers.list(all=True) if container.name == name]
            if containers:
                for container in containers:
                    container.start()
        else:
            startcommand = "%s start %s" % (engine, name)
            if self.host != '127.0.0.1':
                startcommand = "ssh -p %s %s@%s %s" % (self.port, self.user, self.host, startcommand)
            os.system(startcommand)
        return {'result': 'success'}

    def stop_container(self, name):
        engine = self.engine
        if self.containermode:
            containers = [container for container in self.d.containers.list() if container.name == name]
            if containers:
                for container in containers:
                    container.stop()
        else:
            stopcommand = "%s stop %s" % (engine, name)
            if self.host != '127.0.0.1':
                stopcommand = "ssh -p %s %s@%s %s" % (self.port, self.user, self.host, stopcommand)
            os.system(stopcommand)
        return {'result': 'success'}

    def console_container(self, name):
        engine = self.engine
        if self.containermode:
            attachcommand = "%s attach %s" % (engine, name)
            os.system(attachcommand)
        else:
            attachcommand = "%s attach %s" % (engine, name)
            if self.host != '127.0.0.1':
                attachcommand = "ssh -t -p %s %s@%s %s" % (self.port, self.user, self.host, attachcommand)
            os.system(attachcommand)
        return {'result': 'success'}

    def list_containers(self):
        engine = self.engine
        containers = []
        if self.containermode:
            for container in self.d.containers.list(all=True):
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
                    plan = 'kvirt'
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
                containers.append([name, state, source, plan, command, portinfo, ''])
        else:
            containers = []
            lscommand = "%s ps -a --format \"{{.Names}}?{{.Status}}?{{.Image}}?{{.Command}}?{{.Ports}}?" % engine
            lscommand += "{{.Labels}}'\""
            if self.debug:
                print(lscommand)
            if self.host != '127.0.0.1':
                lscommand = "ssh -p %s %s@%s %s" % (self.port, self.user, self.host, lscommand)
            results = os.popen(lscommand).readlines()
            for container in results:
                name, state, source, command, ports, labels = container.split('?')
                labels = labels.replace('map[', '').replace(']', '').replace('\n', '').split(' ')
                plan = 'kvirt'
                for label in labels:
                    if ':' not in label:
                        break
                    label_split = label.split(':')
                    key, value = label_split[0], ':'.join(label_split[1:])
                    if key == 'plan':
                        plan = value
                        break
                if state.startswith('Up'):
                    state = 'up'
                else:
                    state = 'down'
                command = command.strip().replace('"', '')
                containers.append([name, state, source, plan, command, ports, ''])
        return containers

    def exists_container(self, name):
        engine = self.engine
        if self.containermode:
            containers = [container.id for container in self.d.containers.list(all=True) if container.name == name]
            if containers:
                return True
        else:
            existcommand = "%s ps -a --format '{{.Names}}'" % engine
            if self.host != '127.0.0.1':
                existcommand = "ssh -p %s %s@%s %s" % (self.port, self.user, self.host, existcommand)
            results = os.popen(existcommand).readlines()
            for container in results:
                containername = container.strip()
                if containername == name:
                    return True
        return False

    def list_images(self):
        engine = self.engine
        if self.containermode:
            images = []
            for i in self.d.images.list():
                for tag in i.tags:
                    images.append(tag)
        else:
            lsicommand = "%s images --format '{{.Repository}}:{{.Tag}}'" % engine
            if self.host != '127.0.0.1':
                lsicommand = "ssh -p %s %s@%s %s" % (self.port, self.user, self.host, lsicommand)
            images = [image.strip() for image in os.popen(lsicommand).readlines()]
        return sorted(images)
