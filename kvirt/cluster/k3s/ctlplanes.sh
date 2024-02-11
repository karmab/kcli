{% if extra_ctlplane_args %}
{% set extra_args = extra_ctlplane_args %}
{% endif %}

{% if 'ubuntu' in image %}
apt-get -y install curl
{% endif %}
{% if sdn != None and sdn == 'cilium' %}
echo bpffs /sys/fs/bpf bpf defaults 0 0 >> /etc/fstab
mount /sys/fs/bpf
{% endif %}

# The logic below is to achieve the following
# - for cloud providers. If the API is internal and
# this is a HA cluster. Use the IP of the API load-balancer
# - for cloud providers. If the API is NOT internal.
# use the external IP. This in both the HA and single ctlplane case
# - The last to branches is for on-prem. E.g. vSphere/VMWare
# in HA or single ctlplane scenarios.
{% if cloud_api_internal and ctlplanes > 1 %}
export IP={{ api_ip }}
{% elif config_type in ['aws', 'gcp', 'ibmcloud'] %}
export IP={{ "$(curl -s ifconfig.me)" }}
{% elif ctlplanes > 1 %}
export IP={{ api_ip }}
{% else %}
export IP={{ first_ip }}
{% endif %}

# In the case that we're scaling back in ctlplane-0 we need to use another one of
# the ctlplane's as the node to join for ctlplane-0. As ctlplane-0 obviously
# cannot join the cluster 'via' itself.
{% if scale|default(False) and 'ctlplane-0' in name %}
{% set first_ip = '{0}-ctlplane-1'.format(cluster)|kcli_info('ip', client ) %}
{% endif %}

curl -sfL https://get.k3s.io | {{ install_k3s_args|default("") }} K3S_TOKEN={{ token }} sh -s - server --server https://{{ first_ip }}:6443 {{ extra_args|join(" ") }} --tls-san $IP
