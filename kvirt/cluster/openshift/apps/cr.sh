{% for crd in crds %}
{{ crd | waitcrd }}
{% endfor %}
oc create -f cr.yml
