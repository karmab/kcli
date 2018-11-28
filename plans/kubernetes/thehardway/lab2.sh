apt-get -y install bind9utils wget
wget -q --https-only --timestamping https://pkg.cfssl.org/R1.2/cfssl_linux-amd64 https://pkg.cfssl.org/R1.2/cfssljson_linux-amd64
chmod +x cfssl_linux-amd64 cfssljson_linux-amd64
mv cfssl_linux-amd64 /usr/local/bin/cfssl
mv cfssljson_linux-amd64 /usr/local/bin/cfssljson
wget https://storage.googleapis.com/kubernetes-release/release/{{ kubernetes_version }}/bin/linux/amd64/kubectl
chmod +x kubectl
mv kubectl /usr/local/bin
