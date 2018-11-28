export OPENSHIFT_INSTALL_PLATFORM=libvirt
export OPENSHIFT_INSTALL_BASE_DOMAIN={{ domain }}
export OPENSHIFT_INSTALL_CLUSTER_NAME={{ cluster }}
export OPENSHIFT_INSTALL_PULL_SECRET_PATH=/root/coreos_pull.json
export OPENSHIFT_INSTALL_LIBVIRT_URI={{ uri }}
export OPENSHIFT_INSTALL_LIBVIRT_IMAGE=file:///root/rhcos-qemu.qcow2
export OPENSHIFT_INSTALL_EMAIL_ADDRESS={{ email_address }}
export OPENSHIFT_INSTALL_PASSWORD={{ password }}
