# kcli repository

[![](https://dockerbuildbadges.quelltext.eu/status.svg?organization=karmab&repository=kcli)](https://hub.docker.com/r/karmab/kcli/builds/)
[![Build Status](https://travis-ci.org/karmab/kcli.svg?branch=master)](https://travis-ci.org/karmab/kcli)
[![Pypi](http://img.shields.io/pypi/v/kcli.svg)](https://pypi.python.org/pypi/kcli/)
[![Copr](https://copr.fedorainfracloud.org/coprs/karmab/kcli/package/kcli/status_image/last_build.png)](https://copr.fedorainfracloud.org/coprs/karmab/kcli/package/kcli)
[![](https://images.microbadger.com/badges/image/karmab/kcli.svg)](https://microbadger.com/images/karmab/kcli "Get your own image badge on microbadger.com")
[![Visit our IRC channel](https://kiwiirc.com/buttons/irc.freenode.net/kcli.png)](https://kiwiirc.com/client/irc.freenode.net/#kcli)

![Screenshot](kcli-small.png)

This tool is meant to interact with existing virtualization providers (libvirt, kubevirt, ovirt, openstack, gcp and aws) and to easily deploy and customize vms from cloud images.

You can also interact with those vms (list, info, ssh, start, stop, delete, console, serialconsole, add/delete disk, add/delete nic,...)

Futhermore, you can deploy vms using predefined profiles, several at once using plan files or entire products for which plans were already created for you

Refer to the [documentation](https://kcli.readthedocs.io) for more information

## Getting Started

```
kcli download image centos7
kcli create vm -i centos7
kcli list vm
kcli ssh vm
kcli delete vm
```

##  What you can do

- Interact with all the virtualization providers using a single tool
- Declare all your objects(vm, containers, networks, ansible playbooks,...) in a single yaml plan file with a simple syntax
- Customize a plan deployment using parameters and jinja templating
- Adjust vms from a plan (memory, cpu, flavor, disks and nics) to match what's defined in the plans
- Inject all configuration with cloudinit/ignition or the equivalent in cloud providers
- Use profiles to launch vms with same hardware characteristics
- Launch a plan from an url
- Share your plan or use existing ones from github repo as products
- Use the existing plans to deploy kubernetes, openshift, openstack, ovirt, kubevirt, ....
- Use the existing cloud images for each distribution
- Easily share private keys between your vms
- Handle dns entries for the vms
- Automatically subscribe your rhel vms
- Get a push button notification when a vm has finished its deployment
- Alternatively use web UI to do the same

## Demo!

[![asciicast](https://asciinema.org/a/153423.png)](https://asciinema.org/a/153423?autoplay=1)

## Contributors

See [contributors on GitHub](https://github.com/karmab/kcli/graphs/contributors)

## Copyright

Copyright 2017 Karim Boumedhel

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## Problems?

Open an issue !
Or drop by #kcli channel on IRC

Mc Fly!!!

karmab
