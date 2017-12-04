sleep 40
gluster peer probe glusterb.example.com
sleep 15
gluster volume create testkvol replica 2 \
glustera:/bricks/brick-glustera-1/brick \
glusterb:/bricks/brick-glusterb-1/brick \
glustera:/bricks/brick-glustera-2/brick \
glusterb:/bricks/brick-glusterb-2/brick
gluster volume set testkvol stat-prefetch off
gluster volume set testkvol server.allow-insecure on
gluster volume set testkvol storage.batch-fsync-delay-usec 0
gluster volume set testkvol nfs.disable off
gluster volume start testkvol
gluster volume bitrot testkvol enable
gluster volume bitrot testkvol scrub-frequency daily
