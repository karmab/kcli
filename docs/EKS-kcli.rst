EKS Workflow
============

This page highlights an example workflow using kcli with AWS EKS. In the workflow it uses ``myeks`` as the clustername and AWS keypair name. It was deployed and tested in ``us-east-1`` region (but should work in other regions).

This workflow also introduces concepts around EKS that you might not be familiar with.

-  EKS Auto Mode - released 2024
-  EKS byocni (Bring Your Own CNI) - released 2024
-  Pod identity - release Nov 2023.
-  cilium CNI (instead of AWS)\*

\*other CNIs can be used

Pre-Requisite tools and Requirements
------------------------------------

1. AWS cli
2. helm cli
3. cilium cli (optional)
4. kcli
5. boto3 and dependencies
6. kubectl cli
7. An AWS account

AWS Role Creation (optional)
----------------------------

Specific role(s) can be created in AWS which can be used by kcli in the provisioning process for the control plane and/or worker nodes if you have specific requirements.

If you don’t create role(s) default ones will be created by kcli in the cluster creation step.

-  Example Roles and attached policies for control plane and worker nodes

   1. ROLE name = eks-ctlplane (with eks.amazonaws.com trust relationship)

      -  AmazonEBSCSIDriverPolicy
      -  AmazonEC2ContainerRegistryReadOnly
      -  AmazonEKS_CNI_Policy
      -  AmazonEKSBlockStoragePolicy
      -  AmazonEKSClusterPolicy

   2. ROLE name = eks-worker (with ec2.amazonaws.com trust relationship)

      -  AmazonEBSCSIDriverPolicy
      -  AmazonEC2ContainerRegistryReadOnly
      -  AmazonEKS_CNI_Policy
      -  AmazonEKSBlockStoragePolicy
      -  AmazonEKSWorkerNodePolicy

Create Cluster
--------------

OS distributions aren’t always up to date with the latest/newer boto3 and botocore versions from AWS. This means that at times kcli will fail due to missing features because of the installed OS version of boto3/botocore.

So this example workflow uses a virtual environment to ensure you have the latest versions.

-  Create virtual environment and install kcli/boto3

.. code:: bash

   mkdir kcli
   cd kcli
   python3 -m venv kcli-boto3
   source kcli-boto3/bin/activate
   pip list
   pip install setuptools wheel
   pip3 install kcli
   pip install boto3
   pip list
   kcli version
   #when finished with the virtual environment
   #deactivate

-  Update aws credentials in kcli config file and variables

.. code:: bash

   vim ~/.kcli/config.yml
       aws:
       type: aws
       access_key_id: XXXXXXXXXXXX
       access_key_secret: YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY
       region: us-east-1
       keypair: myekskey

   # you might choose to update your AWS profile
   #aws configure --profile kcli
   #export AWS_PROFILE=kcli

   export AWS_ACCESS_KEY_ID=$(grep access_key_id ~/.kcli/config.yml| awk -F: '{print $2}'| sed 's/ //g')
   export AWS_SECRET_ACCESS_KEY=$(grep access_key_secret ~/.kcli/config.yml| awk -F: '{print $2}'| sed 's/ //g')

-  Test AWS credentials

Make sure AWS is functioning - this command should either return nothing or your buckets, but shouldn’t fail if the environment variables have been set correctly.

.. code:: bash

   aws s3 ls

-  Import keypair into AWS

In the ~/.kcli/config.yaml you specified a key that will be injected into the deployed cluster. So here import the key or if you already have a key in AWS then you can skip this, just make sure you reference the existing AWS key name in the config.yaml file.

.. code:: bash

   # ssh-keygen -b 4096 -t rsa or ssh-keygen -b 4096 -t ed25519 etc...
   aws ec2 import-key-pair --key-name "myekskey" --public-key-material fileb://~/.ssh/id_rsa.pub

-  Create cluster (BYOCNI)

In this workflow we pass the parameters as arguments to the kcli create command. Alternatively you could add them to a parameter file and call the parameter file with the kcli create command.

Alternative kcli create cluster command examples (ymmv):-

   *You can create a cluster with AWS-CNI like this to have kcli deploy standard set of addons this will also deploy the cluster in Auto Mode*

..

   ``kcli create kube eks myeks``

   *You could also deploy AWS-CNI without Auto Mode and some addons like this*

..

   ``kcli create kube eks -P default_addons=false -P apps=[coredns,vpc-cni,kube-proxy,aws-ebs-csi-driver,eks-pod-identity-agent] myeks``

   *Here you add additional arguments to specify separate roles for control plane and workers*

..

   ``kcli create kube eks -P subnet=subnet-0f4e6564cd0052731 -P extra_subnets=[subnet-0ea77dff7cd0dda6d] -P default_addons=False -P apps=[coredns,vpc-cni,kube-proxy,aws-ebs-csi-driver,eks-pod-identity-agent] -P ctlplane_role=eks-ctlplane -P worker_role=eks-worker myeks``

For this workflow we will create a BYOCNI cluster (no aws-cni or kube-proxy), disable Auto Mode and install cilium on the cluster.

.. code:: bash

   # list available subnets. Choose from the list and use them as arguments to kcli create or let kcli autodetect when creating.

   kcli list subnets

   # you will see something like this and can pick the subnets you want to use in the create command

   Listing Subnets...
   +--------------------------+------------+----------------+--------------------------+-----------------------+
   |          Subnet          |    Zone    |      Cidr      |            Id            | Network               |
   +--------------------------+------------+----------------+--------------------------+-----------------------+
   | subnet-00455945f5834b4f6 | us-east-1d | 172.31.32.0/20 | subnet-00455945f5834b4f6 | vpc-0a577c7b378354b02 |
   | subnet-01a28a456b7587e91 | us-east-1a | 172.31.0.0/20  | subnet-01a28a456b7587e91 | vpc-0a577c7b378354b02 |
   | subnet-01bf43e04191244d4 | us-east-1b | 172.31.80.0/20 | subnet-01bf43e04191244d4 | vpc-0a577c7b378354b02 |
   | subnet-031627ea5f56a0fda | us-east-1f | 172.31.64.0/20 | subnet-031627ea5f56a0fda | vpc-0a577c7b378354b02 |
   | subnet-0707e63fab3c1eec4 | us-east-1c | 172.31.16.0/20 | subnet-0707e63fab3c1eec4 | vpc-0a577c7b378354b02 |
   | subnet-0d69ee6b2a02fb637 | us-east-1e | 172.31.48.0/20 | subnet-0d69ee6b2a02fb637 | vpc-0a577c7b378354b02 |
   +--------------------------+------------+----------------+--------------------------+-----------------------+

   # to list cluster parameters you can then choose which ones you want to alter in create command using a parameter file or pass as an arguments (-P)

   kcli info cluster eks

   # you should see something like this

   Auto mode is used by default
   default add-ons can be disabled if a custom CNI is required
   OIDC configuration can be achieved by setting the relevant oidc_* variables
   ami_type: None
   auto_mode: True
   capacity_type: None
   ctlplane_role: None
   default_addons: True
   disk_size: None
   extended_support: True
   extra_networks: []
   extra_subnets: None
   flavor: None
   logging: False
   logging_types: ['api']
   network: default
   oidc_client_id: None
   oidc_group_claim: cognito:groups
   oidc_issuer_url: None
   oidc_name: oidc-config
   oidc_username_claim: email
   role: None
   security_group: None
   subnet: None
   version: None
   worker_role: None
   workers: 2
   zonal_shift: False

   # get the instance-types or flavors - then you can use that in the create command if required

   kcli get instance-type

   # this kcli create example disables all addons, specifies subnets, enables coredns, ebs-csi and pod identity addons. It will deploy the default instance type in EKS as it isn't specified

   kcli create kube eks -P subnet=subnet-049d0829d2985b950 -P extra_subnets=[subnet-076237bed7ca7bd5f] -P default_addons=False -P apps=[coredns,aws-ebs-csi-driver,eks-pod-identity-agent] myeks

   # eventually you will see this - notice it has created the needed AWS roles for control plane and workers

   Disabling network add-ons (and automode)
   Creating ctlplane role kcli-eks-ctlplane
   Using ctlplane role kcli-eks-ctlplane
   Creating worker role kcli-eks-worker
   Using worker role kcli-eks-worker
   Using subnet subnet-00455945f5834b4f6 as default
   Using subnet subnet-031627ea5f56a0fda as extra subnet
   Waiting for cluster myeks to be created
   Creating nodegroup myeks
   Kubernetes cluster myeks deployed!!!
   INFO export KUBECONFIG=(kcli-boto3)$HOME/.kcli/clusters/myeks/auth/kubeconfig
   INFO export PATH=(kcli-boto3)$PWD:(kcli-boto3)$PATH
   Adding app coredns
   Issue adding app coredns
   Adding app aws-ebs-csi-driver
   Issue adding app aws-ebs-csi-driver
   Adding app eks-pod-identity-agent

-  Export the kubeconfig and check all pods are in a pending state.

.. code:: bash

   export KUBECONFIG=(kcli-boto3)$HOME/.kcli/clusters/myeks/auth/kubeconfig
   # after the create command has finished give things 2mins to complete - things are still rolling out
   kubectl get pods -A

-  Install cilium CNI - HELM or CLI

If you have deployed using the byocni kcli create command in the previous sections then you will need to deploy a CNI - this example uses cilium. if you have deployed AWS CNI or are using another CNI then skip this step.

.. code:: bash

   # get the control plane API address
   export API_SERVER=$(kubectl cluster-info | grep Kubernetes | awk -F/ '{print $3}')

   # this will automatically get the API address in one command and install cilium using helm

   helm upgrade --install --namespace kube-system --repo https://helm.cilium.io cilium cilium  --set cluster.name=myeks --set k8sServiceHost=${API_SERVER} --set k8sServicePort=443

   # ALTERNATIVE via cilium CLI - Install cilium and enables Ingress Controller
   cilium install  --set cluster.name=myeks --set k8sServiceHost=${API_SERVER} --set k8sServicePort=443 --set ingressController.enabled=true --set ingressController.loadbalancerMode=dedicated

-  Check to see that pods are now running and deploy a test pod

.. code:: bash

   #all namespaces
   kubectl get pods -A
   # in default namespace
   kubectl run nginx --image=nginx
   kubectl get pods

Pod Identity
------------

Clusters deployed by kcli won’t have access to AWS services like S3 or EBS etc…

Pod identity enables us to tie kubernetes Service Accounts to AWS roles with attached policies to allow access to AWS services. *It is the replacement process for IRSA*

   Pod identity doesn’t require OpenID provider

*The process described below can be used to tie other kubernetes service accounts to AWS roles which have access to aws services*

Using EBS as an example we can tie the EBS controller service account to a AWS role with an attached policy for managing EBS.

-  EBS storage

.. code:: bash

   #Create podidentity-trust-relationship.json
   cat <<EOF >podidentity-trust-relationship.json
   {
       "Version": "2012-10-17",
       "Statement": [
           {
               "Sid": "AllowEksAuthToAssumeRoleForPodIdentity",
               "Effect": "Allow",
               "Principal": {
                   "Service": "pods.eks.amazonaws.com"
               },
               "Action": [
                   "sts:AssumeRole",
                   "sts:TagSession"
               ]
           }
       ]
   }
   EOF
   # create a role with the trust policy for Pod identity attached
   aws iam create-role --role-name ebs-role --assume-role-policy-document file://podidentity-trust-relationship.json --description "EBS role"

   # you can list the policies available
   #aws iam list-policies | grep CSI

   # You could create a policy document 
   # example of one for EBS - https://raw.githubusercontent.com/kubernetes-sigs/aws-ebs-csi-driver/master/docs/example-iam-policy.json

   # and then create the policy in AWS with POLICY_NAME
   # aws iam create-policy --policy-name POLICY_NAME --policy-document file://POLICY_DOC --query Policy.Arn --output text

   # and then attach the custom policy to the custom role
   #aws iam attach-role-policy --role-name ebs-role --policy-arn=arn:aws:iam::XXXXXX:policy/POLICY_NAME

   # In this case we are using an existing AWS managed policy and attaching it to the role
   aws iam attach-role-policy --role-name ebs-role --policy-arn=arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy
   # list policies attached to the role
   aws iam list-attached-role-policies --role-name ebs-role --output text
   # list the pod identities in your cluster - should be empty (unless you have created other associations)
   aws eks list-pod-identity-associations --cluster-name myeks

   # Get the account id
   export ACCTID=$(aws sts get-caller-identity --query "Account" --output text)

   # associate the role with the kubernetes service account - we automatically get the account ID
   aws eks create-pod-identity-association --cluster-name myeks --role-arn arn:aws:iam::${ACCTID}:role/ebs-role --namespace kube-system --service-account ebs-csi-controller-sa

   # restart the pods for ebs-csi so it picks up the new AWS credentials that are injected by pod identity
   kubectl rollout restart -n kube-system deployment ebs-csi-controller
   # check the AWS credentials are in the pod
   kubectl describe pod -n kube-system ebs-csi-controller-7c77d8cc97-8hgg2 | grep AWS

   # you will also need to set the default storage class as it is no longer set by default. In this case only gp2 is setup, so make it the default.
   kubectl annotate sc gp2 storageclass.kubernetes.io/is-default-class=true

   # optionally test creation of a EBS backed pv/pvc
   cat <<EOF > test-ebs-pvc.yaml
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: ebs-storage
   spec:
     accessModes:
       - ReadWriteOnce
     storageClassName: gp2
     resources:
       requests:
         storage: 2Gi
   EOF

   # create pvc

   kubectl apply -f test-ebs-pvc.yaml

   # create deployment using pvc which will trigger pv and EBS allocation
   cat <<EOF > test-ebs-pod.yaml
   apiVersion: v1
   kind: Pod
   metadata:
     labels:
       run: test-ebs
     name: test-ebs
   spec:
     containers:
     - image: nginx
       name: test-ebs
       volumeMounts:
         - mountPath: /var/log/nginx
           name: nginx-logs
     volumes:
       - name: nginx-logs
         persistentVolumeClaim:
           claimName: ebs-storage
   EOF

   # create pod with pvc
   kubectl apply -f test-ebs-pod.yaml

Useful commands
---------------

.. code:: bash

   # changes depending on what type of cluster eks, generic etc...)
   kcli list app
   kcli list subnets
   kcli list flavors
   kcli info app coredns
   kcli info app aws-ebs-csi-driver
   kcli info cluster eks
   kcli create bucket myeks
   kcli create app aws-ebs-csi-driver
   kcli delete cluster eks myeks
