sleep 40
gluster peer probe glusterb.example.com
sleep 15
gluster volume create [[ volume ]] replica 2 \
glustera:/bricks/brick-glustera-1/brick \
glusterb:/bricks/brick-glusterb-1/brick \
glustera:/bricks/brick-glustera-2/brick \
glusterb:/bricks/brick-glusterb-2/brick
gluster volume set [[ volume ]] stat-prefetch off
gluster volume set [[ volume ]] server.allow-insecure on
gluster volume set [[ volume ]] storage.batch-fsync-delay-usec 0
gluster volume set [[ volume ]] nfs.disable off
gluster volume start [[ volume ]]
gluster volume bitrot [[ volume ]] enable
gluster volume bitrot [[ volume ]] scrub-frequency daily
