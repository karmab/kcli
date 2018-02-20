Pull the latest image:

.. code:: shell

    docker pull karmab/kcli

If running locally, launch it with:

.. code:: shell

    docker run --rm -v /var/run/libvirt:/var/run/libvirt -v ~/.ssh:/root/.ssh karmab/kcli

If using a remote libvirt hypervisor, launch it with your local .kcli
directory pointing to this hypervisor and providing your ssh keys too

.. code:: shell

    docker run -it --rm -v ~/.kcli:/root/.kcli -v ~/.ssh:/root/.ssh karmab/kcli

The entrypoint is defined as kcli, so you can type commands directly as:

.. code:: shell

    docker run -it --rm -v ~/.kcli:/root/.kcli -v ~/.ssh:/root/.ssh karmab/kcli list

As a bonus, you can alias kcli and run kcli as if it is installed
locally instead a Docker container:

.. code:: shell

    alias kcli = "docker run -it --rm -v ~/.kcli:/root/.kcli -v ~/.ssh:/root/.ssh karmab/kcli"

If you need a shell access to the container, use the following:

.. code:: shell

    alias kcli = "docker run -it --rm -v ~/.kcli:/root/.kcli -v ~/.ssh:/root/.ssh --entrypoint=/bin/bash karmab/kcli"

Note that the container cant be used for virtualbox ( i tried hard but
there's no way that will work...)

For the web access, you can use

.. code:: shell

    alias kweb = "docker run --rm -v ~/.kcli:/root/.kcli -v ~/.ssh:/root/.ssh --entrypoint=/usr/bin/kweb karmab/web"
