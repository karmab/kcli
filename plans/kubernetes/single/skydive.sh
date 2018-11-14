oc new-project skydive
oc adm policy add-scc-to-user privileged -z default -n skydive
oc apply -f skydive.yml
oc new-app --template=skydive -n skydive
