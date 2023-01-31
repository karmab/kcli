FROM quay.io/karmab/kcli
MAINTAINER Karim Boumedhel <karimboumedhel@gmail.com>
ADD kubectl /usr/local/bin/kubectl
RUN chmod 777 /usr/local/bin/kubectl
ADD handlers.py /
ADD crd.yml /
RUN pip3 install kopf 
ENTRYPOINT ["kopf","run","/handlers.py", "--verbose"]
