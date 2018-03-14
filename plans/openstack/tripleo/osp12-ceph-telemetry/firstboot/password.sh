#!/bin/bash
# Permit root login over SSH
sed -i 's/.*ssh-rsa/ssh-rsa/' /root/.ssh/authorized_keys
sed -i 's/PasswordAuthentication.*/PasswordAuthentication yes/g' /etc/ssh/sshd_config
sed -i 's/ChallengeResponseAuthentication.*/ChallengeResponseAuthentication yes/g' /etc/ssh/sshd_config

systemctl restart sshd
# Update the root password to something we know
echo maqueta1234 | sudo passwd root --stdin
