USER="admin"
PASSWD="unix1234"
jq . << EOF > ~/instackenv.json
{
  "nodes": [
    {
      "arch": "x86_64",
      "name": "ctrl01",
      "pm_user": "${USER}",
      "pm_addr": "127.0.0.1",
      "pm_password": "${PASSWD}",
      "pm_port": "6231",
      "pm_type": "pxe_ipmitool",
      "mac": [
        "aa:bb:cc:dd:ee:01"
      ],
      "cpu": "4"
    },
    {
      "arch": "x86_64",
      "name": "ctrl02",
      "pm_user": "${USER}",
      "pm_addr": "127.0.0.1",
      "pm_password": "${PASSWD}",
      "pm_port": "6232",
      "pm_type": "pxe_ipmitool",
      "mac": [
        "aa:bb:cc:dd:ee:02"
      ],
      "cpu": "4"
    },
    {
      "arch": "x86_64",
      "name": "ctrl03",
      "pm_user": "${USER}",
      "pm_addr": "127.0.0.1",
      "pm_password": "${PASSWD}",
      "pm_port": "6233",
      "pm_type": "pxe_ipmitool",
      "mac": [
        "aa:bb:cc:dd:ee:03"
      ],
      "cpu": "4"
    },
    {
      "arch": "x86_64",
      "name": "c01",
      "pm_user": "${USER}",
      "pm_addr": "127.0.0.1",
      "pm_password": "${PASSWD}",
      "pm_port": "6234",
      "pm_type": "pxe_ipmitool",
      "mac": [
        "aa:bb:cc:dd:ee:04"
      ],
      "cpu": "4"
    },
    {
      "arch": "x86_64",
      "name": "c02",
      "pm_user": "${USER}",
      "pm_addr": "127.0.0.1",
      "pm_password": "${PASSWD}",
      "pm_port": "6235",
      "pm_type": "pxe_ipmitool",
      "mac": [
        "aa:bb:cc:dd:ee:05"
      ],
      "cpu": "4"
    },
    {
      "arch": "x86_64",
      "name": "ceph01",
      "pm_user": "${USER}",
      "pm_addr": "127.0.0.1",
      "pm_password": "${PASSWD}",
      "pm_port": "6236",
      "pm_type": "pxe_ipmitool",
      "mac": [
        "aa:bb:cc:dd:ee:06"
      ],
      "cpu": "4"
    },
    {
      "arch": "x86_64",
      "name": "ceph02",
      "pm_user": "${USER}",
      "pm_addr": "127.0.0.1",
      "pm_password": "${PASSWD}",
      "pm_port": "6237",
      "pm_type": "pxe_ipmitool",
      "mac": [
        "aa:bb:cc:dd:ee:07"
      ],
      "cpu": "4"
    },
    {
      "arch": "x86_64",
      "name": "ceph03",
      "pm_user": "${USER}",
      "pm_addr": "127.0.0.1",
      "pm_password": "${PASSWD}",
      "pm_port": "6238",
      "pm_type": "pxe_ipmitool",
      "mac": [
        "aa:bb:cc:dd:ee:08"
      ],
      "cpu": "4"
    },
    {
      "arch": "x86_64",
      "name": "telemetry01",
      "pm_user": "${USER}",
      "pm_addr": "127.0.0.1",
      "pm_password": "${PASSWD}",
      "pm_port": "6239",
      "pm_type": "pxe_ipmitool",
      "mac": [
        "aa:bb:cc:dd:ee:09"
      ],
      "cpu": "4"
    },
   {
      "arch": "x86_64",
      "name": "telemetry02",
      "pm_user": "${USER}",
      "pm_addr": "127.0.0.1",
      "pm_password": "${PASSWD}",
      "pm_port": "6240",
      "pm_type": "pxe_ipmitool",
      "mac": [
        "aa:bb:cc:dd:ee:10"
      ],
      "cpu": "4"
    }


  ]
}
EOF
