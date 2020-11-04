REGISTRY_USER={{ disconnected_user if disconnected_user != None else 'dummy' }}
REGISTRY_PASSWORD={{ disconnected_password if disconnected_password != None else 'dummy' }}
image=$1
podman login -u $REGISTRY_USER -p $REGISTRY_PASSWORD $(hostname -f):5000
podman pull $image
short=$(echo $image | cut -d: -f1)
tag=$(podman images | grep $short | awk '{print $3}')
image_registry=$(echo $image | cut -d/ -f1)
image_name=$(echo $image | sed "s@$image_registry/@@")
podman tag $tag $(hostname -f):5000/$image_name
podman push $(hostname -f):5000/$image_name
