FROM alpine:3.10

MAINTAINER Karim Boumedhel <karimboumedhel@gmail.com>

LABEL name="karmab/kcli" \
      maintainer="karimboumedhel@gmail.com" \
      vendor="Karmalabs" \
      version="latest" \
      release="0" \
      summary="Virtualization wrapper" \
      description="Virtualization wrapper"

EXPOSE 9000

RUN apk add --update --no-cache g++ gcc libvirt libvirt-dev python3-dev openssh-client curl curl-dev libressl-dev libxml2-dev git linux-headers libffi-dev cdrkit xauth bash

# Group the pip installation
RUN pip3 install --no-cache-dir -e git+https://github.com/karmab/kcli.git#egg=kcli[all]

ADD klist.py /usr/bin
RUN chmod o+x /usr/bin/klist.py && touch /i_am_a_container && echo eval \"\$\(register-python-argcomplete kcli\)\" >> /root/.bashrc && apk del g++ gcc libvirt-dev curl-dev libressl-dev libxml2-dev git linux-headers libffi-dev

ENTRYPOINT ["/usr/bin/kcli"]
CMD ["-h"]
