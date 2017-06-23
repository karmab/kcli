yum -y install openshift-ansible-playbooks
ssh-keyscan -H lb.karmalabs.local >> ~/.ssh/known_hosts
ssh-keyscan -H master01.karmalabs.local >> ~/.ssh/known_hosts
ssh-keyscan -H master02.karmalabs.local >> ~/.ssh/known_hosts
ssh-keyscan -H master03.karmalabs.local >> ~/.ssh/known_hosts
ssh-keyscan -H node01.karmalabs.local >> ~/.ssh/known_hosts
ssh-keyscan -H node02.karmalabs.local >> ~/.ssh/known_hosts
ssh-keyscan -H node03.karmalabs.local >> ~/.ssh/known_hosts
