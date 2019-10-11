
hostcreate_examples = """# Add a kvm host
$ kcli create host kvm -H 192.168.1.6 twix

# Add a aws host
$ kcli create host aws --access_key_id xxx  --access_key_secret xxx  -k KEYPAIR mypair -r eu-west-3 myaws

# Add a gcp host
$ kcli create host gcp --credentials ~/.kcli/xx.json --project myproject-209909 --zone us-central1-b mygcp

# Add a ovirt host
$ kcli create host ovirt -c mycluster -d mydatacenter -H 192.168.1.2 -u admin@internal -p pass -o org1 --pool x myovirt

# Add a vsphere host
$ kcli create host vsphere -c mycluster -d mydatacenter -H 192.168.1.3 -u admin@xxx.es -p pass mysphere

# Add a openstack host
$ kcli create host openstack --auth-url http://10.19.114.91:5000/v3 -u admin -p pass --project myproject myosp

# Add a kubevirt host using existing k8s credentials
$ kcli create host kubevirt mykubevirt
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
