contrail_manifests = ['openshift/manifests/00-contrail-01-namespace.yaml',
                      'openshift/manifests/00-contrail-02-admin-password.yaml',
                      'openshift/manifests/00-contrail-02-rbac-auth.yaml',
                      # 'openshift/manifests/00-contrail-02-registry-secret.yaml',
                      'openshift/manifests/00-contrail-03-cluster-role.yaml',
                      'openshift/manifests/00-contrail-04-serviceaccount.yaml',
                      'openshift/manifests/00-contrail-05-rolebinding.yaml',
                      'openshift/manifests/00-contrail-06-clusterrolebinding.yaml',
                      'crds/contrail.juniper.net_cassandras_crd.yaml',
                      'crds/contrail.juniper.net_commands_crd.yaml',
                      'crds/contrail.juniper.net_configs_crd.yaml',
                      'crds/contrail.juniper.net_contrailcnis_crd.yaml',
                      'crds/contrail.juniper.net_fernetkeymanagers_crd.yaml',
                      'crds/contrail.juniper.net_contrailmonitors_crd.yaml',
                      'crds/contrail.juniper.net_contrailstatusmonitors_crd.yaml',
                      'crds/contrail.juniper.net_controls_crd.yaml',
                      'crds/contrail.juniper.net_keystones_crd.yaml',
                      'crds/contrail.juniper.net_kubemanagers_crd.yaml',
                      'crds/contrail.juniper.net_managers_crd.yaml',
                      'crds/contrail.juniper.net_memcacheds_crd.yaml',
                      'crds/contrail.juniper.net_postgres_crd.yaml',
                      'crds/contrail.juniper.net_provisionmanagers_crd.yaml',
                      'crds/contrail.juniper.net_rabbitmqs_crd.yaml',
                      'crds/contrail.juniper.net_swiftproxies_crd.yaml',
                      'crds/contrail.juniper.net_swifts_crd.yaml',
                      'crds/contrail.juniper.net_swiftstorages_crd.yaml',
                      'crds/contrail.juniper.net_vrouters_crd.yaml',
                      'crds/contrail.juniper.net_webuis_crd.yaml',
                      'crds/contrail.juniper.net_zookeepers_crd.yaml',
                      'openshift/releases/R2011/manifests/00-contrail-08-operator.yaml',
                      'openshift/releases/R2011/manifests/00-contrail-09-manager.yaml',
                      'openshift/manifests/cluster-network-02-config.yml']


contrail_openshifts = ['openshift/openshift/99_master-iptables-machine-config.yaml',
                       'openshift/openshift/99_master-kernel-modules-overlay.yaml',
                       'openshift/openshift/99_master_network_functions.yaml',
                       'openshift/openshift/99_master_network_manager_stop_service.yaml',
                       'openshift/openshift/99_master-pv-mounts.yaml',
                       'openshift/openshift/99_worker-iptables-machine-config.yaml',
                       'openshift/openshift/99_worker-kernel-modules-overlay.yaml',
                       'openshift/openshift/99_worker_network_functions.yaml',
                       'openshift/openshift/99_worker_network_manager_stop_service.yaml']

contrail_manifests = ['https://raw.githubusercontent.com/Juniper/contrail-operator/R2011/deploy/%s' % asset for
                      asset in contrail_manifests]
contrail_openshifts = ['https://raw.githubusercontent.com/Juniper/contrail-operator/R2011/deploy/%s' % asset for
                       asset in contrail_openshifts]
