yum -y install openshift-ansible-playbooks
ssh-keyscan -H lb.karmalabs.com >> ~/.ssh/known_hosts
ssh-keyscan -H master1.karmalabs.com >> ~/.ssh/known_hosts
ssh-keyscan -H master2.karmalabs.com >> ~/.ssh/known_hosts
ssh-keyscan -H master3.karmalabs.com >> ~/.ssh/known_hosts
ssh-keyscan -H node0.karmalabs.com >> ~/.ssh/known_hosts
ssh-keyscan -H node1.karmalabs.com >> ~/.ssh/known_hosts
ssh-keyscan -H node2.karmalabs.com >> ~/.ssh/known_hosts
