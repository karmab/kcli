{{ csv | wait_csv(namespace) }}

oc create -f cr.yml
