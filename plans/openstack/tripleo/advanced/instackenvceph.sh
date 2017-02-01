USER="root"
jq . << EOF > ~/instackenv.json
{
  "ssh-user": "$USER",
  "ssh-key": "",
  "power_manager": "nova.virt.baremetal.virtual_power_driver.VirtualPowerManager",
  "host-ip": "192.168.101.1",
  "arch": "x86_64",
  "nodes": [
    {
      "pm_addr": "192.168.101.1",
      "pm_password": "$(cat ~/.ssh/id_rsa)",
      "pm_type": "pxe_ssh",
      "mac": [
        "aa:bb:cc:dd:ee:01"
      ],
      "cpu": "2",
      "memory": "4096",
      "disk": "30",
      "arch": "x86_64",
      "pm_user": "$USER"
    },
    {
      "pm_addr": "192.168.101.1",
      "pm_password": "$(cat ~/.ssh/id_rsa)",
      "pm_type": "pxe_ssh",
      "mac": [
        "aa:bb:cc:dd:ee:02"
      ],
      "cpu": "2",
      "memory": "4096",
      "disk": "30",
      "arch": "x86_64",
      "pm_user": "$USER"
    },
    {
      "pm_addr": "192.168.101.1",
      "pm_password": "$(cat ~/.ssh/id_rsa)",
      "pm_type": "pxe_ssh",
      "mac": [
        "aa:bb:cc:dd:ee:03"
      ],
      "cpu": "2",
      "memory": "4096",
      "disk": "30",
      "arch": "x86_64",
      "pm_user": "$USER"
    },
    {
      "pm_addr": "192.168.101.1",
      "pm_password": "$(cat ~/.ssh/id_rsa)",
      "pm_type": "pxe_ssh",
      "mac": [
        "aa:bb:cc:dd:ee:04"
      ],
      "cpu": "2",
      "memory": "4096",
      "disk": "30",
      "arch": "x86_64",
      "pm_user": "$USER"
    },
    {
      "pm_addr": "192.168.101.1",
      "pm_password": "$(cat ~/.ssh/id_rsa)",
      "pm_type": "pxe_ssh",
      "mac": [
        "aa:bb:cc:dd:ee:05"
      ],
      "cpu": "2",
      "memory": "4096",
      "disk": "30",
      "arch": "x86_64",
      "pm_user": "$USER"
    },
    {
      "pm_addr": "192.168.101.1",
      "pm_password": "$(cat ~/.ssh/id_rsa)",
      "pm_type": "pxe_ssh",
      "mac": [
        "aa:bb:cc:dd:ee:06"
      ],
      "cpu": "2",
      "memory": "4096",
      "disk": "30",
      "arch": "x86_64",
      "pm_user": "$USER"
    },
    {
      "pm_addr": "192.168.101.1",
      "pm_password": "$(cat ~/.ssh/id_rsa)",
      "pm_type": "pxe_ssh",
      "mac": [
        "aa:bb:cc:dd:ee:07"
      ],
      "cpu": "2",
      "memory": "4096",
      "disk": "30",
      "arch": "x86_64",
      "pm_user": "$USER"
    }
  ]
}
EOF
