ENCRYPTION_KEY=$(head -c 32 /dev/urandom | base64)
sed "s/ENCRYPTION_KEY/$ENCRYPTION_KEY/" encryption-config.yaml
for instance in controller-0 controller-1 controller-2; do
  scp encryption-config.yaml ${instance}:
done
