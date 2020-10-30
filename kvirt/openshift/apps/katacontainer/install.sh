curl https://raw.githubusercontent.com/openshift/kata-operator/release-{{ openshift_version }}/deploy/deploy.sh | bash
oc apply -f https://raw.githubusercontent.com/openshift/kata-operator/release-{{ openshift_version }}/deploy/crds/kataconfiguration.openshift.io_v1alpha1_kataconfig_cr.yaml
