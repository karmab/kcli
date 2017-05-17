```bash
yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
yum -y install ftp://rpmfind.net/linux/fedora/linux/development/rawhide/Everything/armhfp/os/Packages/p/python2-six-1.10.0-8.fc26.noarch.rpm
yum -y install ftp://fr2.rpmfind.net/linux/fedora-secondary/releases/25/Everything/s390x/os/Packages/p/python2-docker-pycreds-0.2.1-2.fc25.noarch.rpm

cat > /etc/yum.repos.d/kcli.repo <<EOF
[karmab-kcli]
name=Copr repo for kcli owned by karmab
baseurl=https://copr-be.cloud.fedoraproject.org/results/karmab/kcli/fedora-26-x86_64/
type=rpm-md
skip_if_unavailable=True
gpgcheck=0
repo_gpgcheck=0
enabled=1
enabled_metadata=1
EOF
yum -y install kcli
```
