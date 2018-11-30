for i in `seq 1 20` ; do j=`printf "%03d" ${i}` ; sed "s/001/$j/" /root/nfs.yml | oc create -f - ; done
