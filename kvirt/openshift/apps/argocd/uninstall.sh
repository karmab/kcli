oc -n argocd delete route argocd
oc delete -f cr.yml
oc delete -f install.yml
