# kcli repository

[![Build Status](https://travis-ci.org/karmab/kcli.svg?branch=master)](https://travis-ci.org/karmab/kcli)
[![Pypi](http://img.shields.io/pypi/v/kcli.svg)](https://pypi.python.org/pypi/kcli/)
[![Copr](https://copr.fedorainfracloud.org/coprs/karmab/kcli/package/kcli/status_image/last_build.png)](https://copr.fedorainfracloud.org/coprs/karmab/kcli/package/kcli)
[![](https://images.microbadger.com/badges/image/karmab/kcli.svg)](https://microbadger.com/images/karmab/kcli "Get your own image badge on microbadger.com")
[![Visit our IRC channel](https://kiwiirc.com/buttons/irc.freenode.net/kcli.png)](https://kiwiirc.com/client/irc.freenode.net/#kcli)

![Screenshot](kcli.jpg)

This tool is meant to interact with a local/remote libvirt daemon and to easily deploy from templates (using cloudinit).
It will also report IPS for any vm connected to a dhcp-enabled libvirt network and generally for every vm deployed from this client.
Futhermore, you can deploy vms using defined profiles or several at once using plans
There is support for gcp, aws, kubevirt and ovirt 

Refer to the [documentation](https://kcli.readthedocs.io) for more information

## [ChangeLog](https://github.com/karmab/kcli/wiki)

##  What you can do

- Interact with libvirt without XML
- Declare all your objects(vm, containers, networks, ansible,...) in a single yaml file!
- Easily grab and share those files from github
- Easily Test all Red Hat Infrastructure products, and their upstream counterparts
- Easily share private keys between your vms
- Inject all configuration with cloudinit
- Use the default cloud images
- Use a web UI to do it too
- Do all of this in additional providers(gcp, aws, kubevirt, ovirt) using same commands and files

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

Send me a mail at [karimboumedhel@gmail.com](mailto:karimboumedhel@gmail.com) !
Or drop by #kcli channel on IRC

Mc Fly!!!

karmab
