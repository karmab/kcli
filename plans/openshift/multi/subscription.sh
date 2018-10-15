[% if version == '3.11' %]
subscription-manager repos --enable=rhel-7-server-extras-rpms --enable=rhel-7-server-ose-[[ version ]]-rpms --enable=rhel-7-server-ansible-2.6-rpms
[% else %]
subscription-manager repos --enable=rhel-7-server-extras-rpms --enable=rhel-7-server-ose-[[ version ]]-rpms --enable=rhel-7-fast-datapath-rpms --enable=rhel-7-server-ansible-2.5-rpms
[% endif %]
