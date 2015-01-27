This branch enables lcmaps support in Keystone-VOMS.

Sample working lcmaps configuration for testing:
$ cat /etc/lcmaps/lcmaps.db:

vomspoolaccount = "lcmaps_voms_poolaccount.mod"
                  "-gridmapfile /etc/grid-security/grid-mapfile"
                  "-gridmapdir /etc/grid-security/gridmapdir"
vomslocalgroup =  "lcmaps_voms_localgroup.mod"
                  "-groupmapfile /etc/grid-security/groupmapfile"
                  "-mapmin 0"


default:
vomspoolaccount -> vomslocalgroup


$ cat /etc/grid-security/grid-mapfile
"/fedcloud.egi.eu/*" .pool

$ cat /etc/grid-security/groupmapfile
"/fedcloud.egi.eu/*" poolgrp

$ ls -l /etc/grid-security/gridmapdir/
total 0
-rw-rw-r-- 2 keystone keystone 0 Nov 25 11:06 pool01
-rw-rw-r-- 1 keystone keystone 0 Nov 24 17:03 pool02

$ id pool01
uid=1001(pool01) gid=1001(poolgrp) groups=1001(poolgrp)
$ id pool02
uid=1002(pool02) gid=1001(poolgrp) groups=1001(poolgrp)




