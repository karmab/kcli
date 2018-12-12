for i in `seq 1 10` ; do 
    fallocate -l 1G /pv00$i/disk.img
done
