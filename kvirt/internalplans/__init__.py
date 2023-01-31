haproxy = """
parameters:
 image: centos8stream
 name: haproxy
 nets:
 - default
 vms: []
 domain:

{{ image }}:
 type: image

loadbalancer-{{ ports | join('+') }}:
 type: profile
 image: {{ image }}
 nets: {{ nets }}

{{ name }}:
 profile: loadbalancer-{{ ports | join('+') }}
 {% if domain != None %}
 domain: {{ domain }}
 {% endif %}
 files:
  - path: /root/haproxy.cfg
    content:   |
      global
         log         127.0.0.1 local2
         chroot      /var/lib/haproxy
         pidfile     /var/run/haproxy.pid
         maxconn     4000
         user        haproxy
         group       haproxy
         nbproc 4
         daemon
      defaults
        mode        http
        log         global
        option      dontlognull
        # option      httpclose
        # option      httplog
        # option      forwardfor
        # option      redispatch
        stats enable
        stats uri /stats
        stats auth admin:password
        timeout connect 10000
        timeout client 300000
        timeout server 300000
        maxconn     60000
        retries     3
      {% for port in ports %}
      listen {{ name }}_{{ port }}
        bind *:{{ port }}
      {% if port in [80, 443] %}
        mode http
        # option httpchk HEAD {{ checkpath }} HTTP/1.0
      {% else %}
        mode tcp
      {% endif %}
        balance roundrobin
        cookie JSESSIONID prefix
        {% for vm in vms %}
        server {{ vm.name }} {{ vm.ip }}:{{ port }} cookie A check
        {% endfor %}
       {% endfor %}
 cmds:
  - yum -y install haproxy
  - sed -i "s/SELINUX=enforcing/SELINUX=permissive/" /etc/selinux/config
  - setenforce 0
  - cp /root/haproxy.cfg /etc/haproxy
  - systemctl start haproxy
  - systemctl enable haproxy
"""
