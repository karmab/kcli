VERSION={{ previous/{{ tekton_version }} if tekton_version != 'latest' else 'latest' }}
RELEASE={{ 'release.notags.yaml' if engine|default('containerd') == 'crio' else 'release.yaml' }}
kubectl apply -f https://storage.googleapis.com/tekton-releases/pipeline/$VERSION/$RELEASE
