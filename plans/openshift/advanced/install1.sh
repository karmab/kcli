yum -y install openshift-ansible-playbooks
ssh-keyscan -H lb.karmalabs.local >> ~/.ssh/known_hosts
ssh-keyscan -H master1.karmalabs.local >> ~/.ssh/known_hosts
ssh-keyscan -H master2.karmalabs.local >> ~/.ssh/known_hosts
ssh-keyscan -H master3.karmalabs.local >> ~/.ssh/known_hosts
ssh-keyscan -H node0.karmalabs.local >> ~/.ssh/known_hosts
ssh-keyscan -H node1.karmalabs.local >> ~/.ssh/known_hosts
ssh-keyscan -H node2.karmalabs.local >> ~/.ssh/known_hosts
