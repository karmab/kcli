{% if policy_as_code_method == 'gatekeeper' %}
kubectl delete -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/master/deploy/gatekeeper.yaml
{% elif policy_as_code_method == 'kyverno' %}
kubectl delete -f https://raw.githubusercontent.com/kyverno/kyverno/main/definitions/release/install.yaml
{% endif %}
