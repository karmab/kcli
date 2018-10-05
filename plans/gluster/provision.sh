#!/usr/bin/env bash
sleep 40
gluster peer probe gluster02
sleep 15
echo y | gluster volume create [[ volume ]] replica 2 gluster01:/bricks/brick-gluster01-1/brick gluster02:/bricks/brick-gluster02-1/brick gluster01:/bricks/brick-gluster01-2/brick gluster02:/bricks/brick-gluster02-2/brick
gluster volume set [[ volume ]] stat-prefetch off
gluster volume set [[ volume ]] server.allow-insecure on
gluster volume set [[ volume ]] storage.batch-fsync-delay-usec 0
echo y | gluster volume set [[ volume ]] nfs.disable off
gluster volume start [[ volume ]]
gluster volume bitrot [[ volume ]] enable
gluster volume bitrot [[ volume ]] scrub-frequency daily
