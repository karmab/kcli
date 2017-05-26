Pull the latest image:

```Shell
docker pull karmab/kcli
```

If running locally, launch it with:

```Shell
docker run --rm -v /var/run/libvirt:/var/run/libvirt -v ~/.ssh:/root/.ssh karmab/kcli
```

If using a remote libvirt hypervisor, launch it with your local .kcli directory pointing to this hypervisor and providing your ssh keys too

```Shell
docker run --rm -v ~/.kcli:/root/.kcli -v ~/.ssh:/root/.ssh karmab/kcli
```

```Shell
docker run --rm -v ~/.kcli:/root/.kcli -v ~/.ssh:/root/.ssh karmab/kcli
```

The entrypoint is defined as kcli, so you can type commands directly as:

```Shell
docker run --rm -v ~/.kcli:/root/.kcli -v ~/.ssh:/root/.ssh karmab/kcli list
```

As a bonus, you can alias kcli and run kcli as if it is installed locally instead a Docker container:

```Shell
alias kcli = "docker run --rm -v ~/.kcli:/root/.kcli -v ~/.ssh:/root/.ssh karmab/kcli"
```

If you need a shell access to the container, use the following:

```Shell
alias kcli = "docker run --rm -v ~/.kcli:/root/.kcli -v ~/.ssh:/root/.ssh --entrypoint=/bin/bash karmab/kcli"
```

Note that the container cant be used for virtualbox ( i tried hard but there's no way that will work...)

For the web access, you can use

```Shell
alias kweb = "docker run --rm -v ~/.kcli:/root/.kcli -v ~/.ssh:/root/.ssh --entrypoint=/usr/bin/kweb karmab/web"
```
