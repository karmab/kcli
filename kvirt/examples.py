
hostcreate_examples = """# Add a kvm host
$ kcli create host kvm -H 192.168.1.6 twix
"""

vmcreate_examples = """# create a centos vm from image centos7 with a random name
$ kcli create vm -i centos7

# create a centos vm named myvm customizing its memory and cpus
$ kcli create vm -i centos7 -P memory=4096 -P numcpus=4

# pass disks, networks and even cmds
$ kcli create vm -i CentOS-7-x86_64-GenericCloud.qcow2 -P disks=[10,20] -P nets=[default] -P cmds=[yum -y install nc]

# create a vm from a custom profile
$ kcli create vm -p myprofile myvm
"""
