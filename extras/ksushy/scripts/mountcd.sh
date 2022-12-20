#!/bin/bash

iso_url=$1
iso=$(basename ${iso_url})
kcli list isos | grep -q ${iso}
[ "$?" == "0" ] || kcli download iso -u ${iso_url} ${iso}
kcli update vm ${BMC_ENDPOINT} -P iso=$1
