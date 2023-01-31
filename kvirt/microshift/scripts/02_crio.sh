{% if 'rhel' in image %}
subscription-manager repos --enable rhocp-4.8-for-rhel-8-x86_64-rpms
{% else %}
CRIO_VERSION=1.$(kubectl version -o yaml | grep minor | cut -d: -f2 | sed 's/"//g' | xargs)
{% if 'fedora' in image|lower %}
dnf module enable -y cri-o:$CRIO_VERSION
{% else %}
#OS="CentOS_8"
OS=$(cat /etc/redhat-release | awk '{print $1"_"$4"_"$2'})
curl -L -o /etc/yum.repos.d/devel:kubic:libcontainers:stable.repo https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/$OS/devel:kubic:libcontainers:stable.repo
curl -L -o /etc/yum.repos.d/devel:kubic:libcontainers:stable:cri-o:$CRIO_VERSION.repo https://download.opensuse.org/repositories/devel:kubic:libcontainers:stable:cri-o:$CRIO_VERSION/$OS/devel:kubic:libcontainers:stable:cri-o:$CRIO_VERSION.repo
dnf -y install containers-common-1-6.module_el8.6.0+954+963caf36
{% endif %}
{% endif %}
dnf -y install cri-o conntrack cri-tools
sed -i 's@conmon = .*@conmon = "/bin/conmon"@' /etc/crio/crio.conf
systemctl enable --now crio
