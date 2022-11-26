FROM quay.io/karmab/kcli
MAINTAINER Karim Boumedhel <karimboumedhel@gmail.com>
ADD kubectl /usr/local/bin/kubectl
RUN chmod 777 /usr/local/bin/kubectl
ADD . /kopf
RUN pip3 install kopf 
ENTRYPOINT ["kopf","run","/kopf/handlers.py", "--verbose"]
