[%- set versions = {
                  'kilo': '7.0',
                  'liberty': '8',
                  'mitaka': '9',
                  'newton': '10',
                  'ocata': '11',
                  'pike': '12',
                  'queen': '13',
               }
-%]
[%- set versionnumber = version[version]  -%]

[% if version in ['kilo','liberty','mitaka'] %]
subscription-manager repos --enable=rhel-7-server-rh-common-rpms --enable=rhel-7-server-openstack-[[ versionnumber ]]-rpms --enable=rhel-ha-for-rhel-7-server-rpms --enable=rhel-7-server-extras-rpms
[% else %]
subscription-manager repos --enable=rhel-7-server-rh-common-rpms --enable=rhel-7-server-openstack-[[ versionnumber ]]-rpms --enable=rhel-ha-for-rhel-7-server-rpms --enable=rhel-7-server-extras-rpms --enable=rhel-7-server-openstack-[[ versionnumber ]]-devtools-rpms
[% endif %]
