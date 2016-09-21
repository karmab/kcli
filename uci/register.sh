subscription-manager register --force --username=kboumedh@redhat.com --password='r3dhA7$27'
subscription-manager subscribe --pool=8a85f981568e999d01568ed222cd6712
subscription-manager attach --auto
subscription-manager repos --disable="*"
subscription-manager repos --enable=rhel-7-server-rpms
