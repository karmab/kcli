FROM karmab/kcli
MAINTAINER Karim Boumedhel <karimboumedhel@gmail.com>
ADD . /kopf
RUN pip3 install kopf 
ENTRYPOINT ["kopf","run","/kopf/handlers.py", "--verbose"]
