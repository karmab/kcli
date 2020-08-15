export KNATIVE_VERSION={{ 'knative/operator' | githubversion(knative_version) }}
echo "Deploying Knative $KNATIVE_VERSION"
kubectl apply -f https://github.com/knative/operator/releases/download/$KNATIVE_VERSION/operator.yaml
kubectl apply -f - cr_serving.yml
kubectl apply -f - cr_eventing.yml
