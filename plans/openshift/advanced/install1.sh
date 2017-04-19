yum -y install openshift-ansible-playbooks
ssh-keyscan -H lb.example.com >> ~/.ssh/known_hosts
ssh-keyscan -H master1.example.com >> ~/.ssh/known_hosts
ssh-keyscan -H master2.example.com >> ~/.ssh/known_hosts
ssh-keyscan -H master3.example.com >> ~/.ssh/known_hosts
ssh-keyscan -H node0.example.com >> ~/.ssh/known_hosts
ssh-keyscan -H node1.example.com >> ~/.ssh/known_hosts
ssh-keyscan -H node2.example.com >> ~/.ssh/known_hosts
