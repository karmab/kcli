haproxy = """
parameters:
 template: CentOS-7-x86_64-GenericCloud.qcow2
 name: haproxy
 vms: []

[[ name ]]:
 template: [[ template ]]
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
        option      httpclose
        option      httplog
        option      forwardfor
        option      redispatch
        timeout connect 10000
        timeout client 300000
        timeout server 300000
        maxconn     60000
        retries     3
      listen [[ name ]] *:[[ port ]]
        mode http
        stats enable
        stats uri /stats
        stats realm HAProxy\ Statistics
        stats auth admin:decret
        balance roundrobin
        cookie JSESSIONID prefix
        option httpclose
        option forwardfor
        option httpchk HEAD [[ checkpath ]] HTTP/1.0
        [% for vm in vms -%]
        server [[ vm.name ]] [[ vm.ip ]]:[[ port ]] cookie A check
        [% endfor %]
 cmds:
  - yum -y install haproxy
  - cp /root/haproxy.cfg /etc/haproxy
  - systemctl start haproxy
  - systemctl enable haproxy
"""
