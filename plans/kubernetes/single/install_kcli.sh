docker pull karmab/kcli
echo alias kcli=\'docker run --security-opt label:disable -it --rm -v ~/.kube:/root/.kube -v ~/.ssh:/root/.ssh -v ~/.kcli:/root/.kcli karmab/kcli\' >> /root/.bashrc
