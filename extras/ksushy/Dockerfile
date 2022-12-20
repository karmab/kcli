FROM quay.io/karmab/kcli:latest
MAINTAINER Karim Boumedhel <karimboumedhel@gmail.com>

RUN echo 'APT::Install-Recommends "0";' >> /etc/apt/apt.conf && echo 'APT::Install-Suggests "0";' >> /etc/apt/apt.conf && apt-get update && apt-get -y install python3-flask && apt -y autoremove && apt-get clean all

RUN mkdir -p /opt/fakefish/

ADD app/templates /opt/fakefish/templates
ADD scripts /opt/fakefish/custom_scripts

WORKDIR /opt/fakefish/

RUN chown -R 1024 /opt/fakefish/

USER 1024

ENTRYPOINT ["/usr/bin/python3", "-u", "/opt/fakefish/fakefish.py"] 
