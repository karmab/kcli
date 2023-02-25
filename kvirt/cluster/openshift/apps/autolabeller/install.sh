sed -i "s@\\\\\\\1@\\\1@g" install.yml
sed -i "s@\\\\\\\2@\\\3@g" install.yml
sed -i "s@\\\\\\\2@\\\3@g" install.yml
oc create -f install.yml
