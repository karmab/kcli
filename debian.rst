.. code:: bash

    wget -P /root https://packagecloud.io/install/repositories/karmab/kcli/script.deb.sh
    bash /root/script.deb.sh
    ln -s /usr/lib/python2.7/dist-packages/ /usr/lib/python2.7/site-packages
    apt-get install kcli python2.7 python-setuptools python-prettytable python-yaml python-netaddr python-iptools python-flask python2-docker python-requests python-websocket python2-docker-pycreds python-libvirt
