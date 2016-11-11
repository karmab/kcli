mkdir ~/.hammer
wget -O /root/.hammer/cli_config.yml https://raw.githubusercontent.com/karmab/kcli/master/plans/foreman/hammer.yml
chmod 600 ~/.hammer/cli_config.yml
hammer user update --login admin --default-location-id 1 --default-organization-id 1 --locations "$LOCATION" --organizations "$ORG"
