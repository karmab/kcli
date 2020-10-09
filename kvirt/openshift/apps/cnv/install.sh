oc create -f install.yml
{{ 'hyperconverged'| waitcrd }}
oc create -f cr.yml
