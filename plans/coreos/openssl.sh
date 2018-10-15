#!/bin/sh
mkdir -p /etc/kubernetes/ssl
cd /etc/kubernetes/ssl
openssl genrsa -out ca-key.pem 2048
openssl req -x509 -new -nodes -key ca-key.pem -days 10000 -out ca.pem -subj "/CN=kube-ca"
openssl genrsa -out apiserver-key.pem 2048
MASTER_HOST=`ifconfig eth0 | grep "inet " | awk '{print $2}'`
sed -i "s/MASTER_HOST/$MASTER_HOST/" /root/openssl.cnf
openssl req -new -key apiserver-key.pem -out apiserver.csr -subj "/CN=kube-apiserver" -config /root/openssl.cnf
openssl x509 -req -in apiserver.csr -CA ca.pem -CAkey ca-key.pem -CAcreateserial -out apiserver.pem -days 365 -extensions v3_req -extfile /root/openssl.cnf
openssl genrsa -out admin-key.pem 2048
openssl req -new -key admin-key.pem -out admin.csr -subj "/CN=kube-admin"
openssl x509 -req -in admin.csr -CA ca.pem -CAkey ca-key.pem -CAcreateserial -out admin.pem -days 365
chmod 600 *-key.pem
