{{ crd | waitcrd(timeout) }}
oc create -f cr.yml
