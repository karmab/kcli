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
# - For cloud providers: If the API is internal and this is a HA cluster, use the IP of the API load-balancer
# - For cloud providers: If the API is NOT internal, use the external IP. This in both the HA and single ctlplane case
# - The last two branches are for on-prem. E.g. vSphere/VMWare in HA or single ctlplane scenarios.
{% if cloud_api_internal and ctlplanes > 1 %}
export IP={{ api_ip }}
{% elif config_type in ['aws', 'gcp', 'ibmcloud'] %}
export IP={{ "$(curl -s ifconfig.me)" }}
{% elif ctlplanes > 1 %}
export IP={{ api_ip }}
{% else %}
export IP={{ first_ip }}
{% endif %}

# In the case that we're scaling back in first ctlplane we need to use
# one of the other ctlplanes as join node, as first control-plane
# cannot join the cluster by itself.
{% if scale|default(False) and ('ctlplane-0' in name or 'master-0' in name) %}
{% set node_suffix = 'master-1' if 'master-0' in name else 'ctlplane-1' %}
{% set first_ip = '{}-{}'.format(cluster, node_suffix) | kcli_info('ip', client) %}
{% endif %}

curl -sfL https://get.k3s.io | {{ install_k3s_args|default("") }} K3S_TOKEN={{ token }} sh -s - server --server https://{{ first_ip }}:6443 {{ extra_args|join(" ") }} --tls-san $IP
