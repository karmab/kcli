PACKAGES=$(cloudsmith list package karmab/kcli | grep 'python3-kcli.*99.0' | cut -d'|' -f4 | xargs | awk '{$NF=""; print $0}')
[ "$(echo $PACKAGES | wc -w)" == "0" ] && exit 0
for package in $PACKAGES ; do
  cloudsmith delete $package -y
done
