# mass-recovery
Allows a user to mass-recover from Rubrik and caters to various recovery types.

- Export
- Livemount
- Unmount
- Livemount with SVM (Independent queues, fails on VMware NFS limit)
- Livemount with SVM (Queued if VMware NFS limit is hit (brute))
- Livemount with SVM (Configured limit of Livemount concurrency)
  
## Requires
- python3
- requests

## Usage
## Running the script
```
./mass_recover.py [config_file]
```

## Console output with show_progress
```
Getting Rubrik Node Information - Done
Getting VMware Structures - Done
Getting Datastore Map - Done
Getting Recovery Data - Done
Running Recovery
[==========================----------------------------------] 44.0% (44 of 100) Storage vMotion (37 Complete,  2 Running,  5 Queued)
```

## Configuration File

```
{
  "function_threads": 3,
  "limit": 5,
  "in_file": "in_data.csv",
  "function": 'livemount',
  "rubrik_host": "172.21.8.33",
  "rubrik_key": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI5ZDFkYjQ2Yi1iYmEzLTRkMGItYjc5ZC01OGZiYWE4ZTgzOWIiLCJpc3MiOiJlNjY3ZWY4Yi01Y2E2LTQ1OTYtYjBhMi1jMjZjNzVhMGMzMjYiLCJqdGkiOiIxNTgyNzdlZS00M2M0LTRlODYtYjU4NC0xMzA0ZmY3OTI1ZmIifQ.9pAudx3eXYAoe9l2Y_9Qy64FldED9EeGHErE4823EAM",
  "recovery_point": "2019-09-10 21:45:47",
  "show_progress": true,
  "max_livemounts": 2,
  "svm": true,
  "svm_threads": 8,
  "nfs_wait": true,
  "power_on": true,
  "prefix": "pm-test_",
  "max_hosts": 3,
}
```
### Mandatory Configuration -
- function_threads (int) - number of simultaneous operations
- in_file (str) - relative path to input file
- function (str) - one of - export/livemount/unmount/dryrun 
- rubrik_host (str) - ip/fqdn of Rubrik node
- rubrik_key (str) - api token for Rubrik 

### Additional Mandatory Configuration for Exports
- prefix (str) - prefix for exported VM names
- max_hosts (int) - number of esx hosts to export to

### Optional Configuration
- limit (int) - how many records to use from input file, useful for testing
- omit_hosts (arr/str) - esx hosts that we don't want to export to
- show_progress (bool) - set to true to have an idea of progress
- nfs_wait (bool) - wait for NFS datastore availablity (play nice with vmware)
    Note: This will show a failure in vCenter with a subsequent success
- max_livemounts (int) - set an explicit number of concurrent NFS mounts, another way to play nice with VMware
- svm (bool) - set with livemount so that we sVM machines upon mount to original datastore
- svm_threads (int) - set with livemount to put a concurrency on running sVM 
- power_on (bool) - set to power machines on upon exposure to vSphere
- recovery_point - set to date in order to recover latest RP up to that point in time

## Input File
### Example 1
```
Object Name,ESX Cluster,Datastore
fileserver-001,poc01-67-cluster02,PURE-DS1-10TB
fileserver-002,poc01-67-cluster02,PURE-DS1-10TB
fileserver-003,poc01-67-cluster02,PURE-DS1-10TB
fileserver-004,poc01-67-cluster02,PURE-DS1-10TB
fileserver-005,poc01-67-cluster02,PURE-DS1-10TB
fileserver-006,poc01-67-cluster02,PURE-DS1-10TB
```
### Example 2
```
Object Name
fileserver-001
fileserver-002
fileserver-003
fileserver-004
fileserver-005
fileserver-006
```
- Object Name is not optional
- Header row for columns used are not optional
- Undefined Cluster/Datastore will use last known locations
- VMware and Datastore data is cached locally, in the event that 
  recoveries DO NOT kick off, delete the cache/*.ds file and rerun.

## Recommended Configuration Changes
### ESX Hosts 
Below are the default and recommended settings in order to allow for more NFS Datastores to be mounted for the purpose 
of mass livemounts. More details can be found at:  VMW KB: https://kb.vmware.com/s/article/2239 
```
ESXi Settings (defaults):
NFS.MaxVolumes 8
Net.TcpipHeapSize 0 (require host reboot)
Net.TcpipHeapMax 512 (require host reboot)

ESXi Settings (recommended):
NFS.MaxVolumes 256
Net.TcpipHeapSize 32 (require host reboot)
Net.TcpipHeapMax 1536 (require host reboot)
```
### Rubrik Cluster 
Below are the default and recommended settings in order to increase limit for simultaneous exports per node.
```
Rubrik Settings (defaults):
cerebro.exportJobInMemorySemShares 1

Rubrik Settings (recommended):
cerebro.exportJobInMemorySemShares 100
```

## Logging
### Log File Naming
```
logs/mass_export_20190910-173024_1_1_1.log
logs/mass_[function]_[time-stamp]_[threads]_[max_hosts]_[limit]
```

### Log File Output 
<details><summary> Expand </summary>
<p>

```
2019-10-06 20:18:45,547 - root - INFO - linux-minimal-0021 - RP SUCCEED - Snap 2019-10-06T08:27:10.973Z - RP 2019-10-06 20:18:44.376076+00:00)
2019-10-06 20:18:45,572 - root - INFO - linux-minimal-0012 - RP SUCCEED - Snap 2019-10-06T07:00:04.831Z - RP 2019-10-06 20:18:44.381019+00:00)
2019-10-06 20:18:45,840 - root - INFO - linux-minimal-0017 - RP SUCCEED - Snap 2019-10-06T09:16:09.424Z - RP 2019-10-06 20:18:44.671286+00:00)
2019-10-06 20:18:45,856 - root - INFO - linux-minimal-0020 - RP SUCCEED - Snap 2019-10-06T08:32:48.082Z - RP 2019-10-06 20:18:44.677268+00:00)
2019-10-06 20:18:46,009 - root - INFO - linux-minimal-0019 - RP SUCCEED - Snap 2019-10-06T08:46:29.579Z - RP 2019-10-06 20:18:44.714169+00:00)
2019-10-06 20:18:46,195 - root - INFO - linux-minimal-0016 - RP SUCCEED - Snap 2019-10-06T07:00:08.138Z - RP 2019-10-06 20:18:45.085137+00:00)
2019-10-06 20:18:46,274 - root - INFO - linux-minimal-0015 - RP SUCCEED - Snap 2019-10-06T07:00:06.563Z - RP 2019-10-06 20:18:45.092159+00:00)
2019-10-06 20:18:46,372 - root - INFO - linux-minimal-0014 - RP SUCCEED - Snap 2019-10-06T07:00:04.859Z - RP 2019-10-06 20:18:45.179884+00:00)
2019-10-06 20:18:46,393 - root - INFO - linux-minimal-0018 - RP SUCCEED - Snap 2019-10-06T07:00:04.780Z - RP 2019-10-06 20:18:45.090162+00:00)
2019-10-06 20:18:46,458 - root - INFO - linux-minimal-0013 - RP SUCCEED - Snap 2019-10-06T07:00:06.560Z - RP 2019-10-06 20:18:45.257724+00:00)
2019-10-06 20:19:15,157 - root - INFO - linux-minimal-0019 - LM SUCCEEDED - cluster:::RVM162S009991 - 2019-10-07T00:18:44.520Z - 2019-10-07T00:19:12.715Z 
2019-10-06 20:19:16,875 - root - INFO - linux-minimal-0020 - LM SUCCEEDED - cluster:::RVM162S010041 - 2019-10-07T00:18:44.343Z - 2019-10-07T00:19:13.715Z 
2019-10-06 20:19:18,483 - root - INFO - linux-minimal-0019 - SVM QUEUED - DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37 (PURE-DS8-10TB)
2019-10-06 20:19:19,809 - root - INFO - linux-minimal-0019 - SVM RUNNING - PURE-DS8-10TB (DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37)
2019-10-06 20:19:20,144 - root - INFO - linux-minimal-0020 - SVM QUEUED - DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37 (PURE-DS8-10TB)
2019-10-06 20:19:26,387 - root - INFO - linux-minimal-0017 - LM SUCCEEDED - cluster:::RVM162S009999 - 2019-10-07T00:18:44.344Z - 2019-10-07T00:19:22.558Z 
2019-10-06 20:19:26,402 - root - INFO - linux-minimal-0012 - LM SUCCEEDED - cluster:::RVM162S009991 - 2019-10-07T00:18:44.060Z - 2019-10-07T00:19:20.313Z 
2019-10-06 20:19:26,572 - root - INFO - linux-minimal-0021 - LM SUCCEEDED - cluster:::RVM162S010315 - 2019-10-07T00:18:44.040Z - 2019-10-07T00:19:21.185Z 
2019-10-06 20:19:26,621 - root - INFO - linux-minimal-0020 - SVM RUNNING - PURE-DS8-10TB (DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37)
2019-10-06 20:19:29,368 - root - INFO - linux-minimal-0012 - SVM QUEUED - DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37 (PURE-DS8-10TB)
2019-10-06 20:19:29,471 - root - INFO - linux-minimal-0017 - SVM QUEUED - DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37 (PURE-DS8-10TB)
2019-10-06 20:19:30,198 - root - INFO - linux-minimal-0021 - SVM QUEUED - DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37 (PURE-DS8-10TB)
2019-10-06 20:19:30,507 - root - INFO - linux-minimal-0012 - SVM RUNNING - PURE-DS8-10TB (DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37)
2019-10-06 20:19:59,995 - root - INFO - linux-minimal-0020 - SVM SUCCEED - PURE-DS8-10TB (DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37)
2019-10-06 20:20:01,159 - root - INFO - linux-minimal-0019 - SVM SUCCEED - PURE-DS8-10TB (DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37)
2019-10-06 20:20:03,279 - root - INFO - linux-minimal-0012 - SVM SUCCEED - PURE-DS8-10TB (DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37)
2019-10-06 20:20:03,953 - root - INFO - linux-minimal-0017 - SVM RUNNING - PURE-DS8-10TB (DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37)
2019-10-06 20:20:05,307 - root - INFO - linux-minimal-0021 - SVM RUNNING - PURE-DS8-10TB (DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37)
2019-10-06 20:20:31,001 - root - INFO - linux-minimal-0014 - LM SUCCEEDED - cluster:::RVM162S009999 - 2019-10-07T00:20:00.010Z - 2019-10-07T00:20:26.821Z 
2019-10-06 20:20:33,573 - root - INFO - linux-minimal-0014 - SVM QUEUED - DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37 (PURE-DS8-10TB)
2019-10-06 20:20:34,598 - root - INFO - linux-minimal-0014 - SVM RUNNING - PURE-DS8-10TB (DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37)
2019-10-06 20:20:35,226 - root - INFO - linux-minimal-0015 - LM SUCCEEDED - cluster:::RVM162S009999 - 2019-10-07T00:19:58.834Z - 2019-10-07T00:20:31.313Z 
2019-10-06 20:20:37,784 - root - INFO - linux-minimal-0015 - SVM QUEUED - DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37 (PURE-DS8-10TB)
2019-10-06 20:20:48,585 - root - INFO - linux-minimal-0021 - SVM SUCCEED - PURE-DS8-10TB (DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37)
2019-10-06 20:20:49,547 - root - INFO - linux-minimal-0017 - SVM SUCCEED - PURE-DS8-10TB (DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37)
2019-10-06 20:20:49,888 - root - INFO - linux-minimal-0016 - LM SUCCEEDED - cluster:::RVM162S010315 - 2019-10-07T00:20:01.989Z - 2019-10-07T00:20:44.084Z 
2019-10-06 20:20:51,714 - root - INFO - linux-minimal-0016 - SVM QUEUED - DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37 (PURE-DS8-10TB)
2019-10-06 20:20:52,234 - root - INFO - linux-minimal-0015 - SVM RUNNING - PURE-DS8-10TB (DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37)
2019-10-06 20:20:53,192 - root - INFO - linux-minimal-0016 - SVM RUNNING - PURE-DS8-10TB (DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37)
2019-10-06 20:21:13,814 - root - INFO - linux-minimal-0014 - SVM SUCCEED - PURE-DS8-10TB (DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37)
2019-10-06 20:21:17,816 - root - INFO - linux-minimal-0018 - LM SUCCEEDED - cluster:::RVM162S009991 - 2019-10-07T00:20:47.245Z - 2019-10-07T00:21:13.077Z 
2019-10-06 20:21:22,821 - root - INFO - linux-minimal-0018 - SVM QUEUED - DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37 (PURE-DS8-10TB)
2019-10-06 20:21:25,425 - root - INFO - linux-minimal-0015 - SVM SUCCEED - PURE-DS8-10TB (DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37)
2019-10-06 20:21:28,643 - root - INFO - linux-minimal-0018 - SVM RUNNING - PURE-DS8-10TB (DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37)
2019-10-06 20:21:32,727 - root - INFO - linux-minimal-0016 - SVM SUCCEED - PURE-DS8-10TB (DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37)
2019-10-06 20:21:35,724 - root - INFO - linux-minimal-0013 - LM SUCCEEDED - cluster:::RVM162S010315 - 2019-10-07T00:20:48.016Z - 2019-10-07T00:21:31.841Z 
2019-10-06 20:21:37,403 - root - INFO - linux-minimal-0013 - SVM QUEUED - DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37 (PURE-DS8-10TB)
2019-10-06 20:21:38,034 - root - INFO - linux-minimal-0013 - SVM RUNNING - PURE-DS8-10TB (DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37)
2019-10-06 20:22:06,746 - root - INFO - linux-minimal-0018 - SVM SUCCEED - PURE-DS8-10TB (DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37)
2019-10-06 20:22:19,403 - root - INFO - linux-minimal-0013 - SVM SUCCEED - PURE-DS8-10TB (DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37)
2019-10-06 20:22:22,449 - root - INFO - Can Be Recovered : 10
2019-10-06 20:22:22,451 - root - INFO - Successful Livemount : 10
2019-10-06 20:22:22,453 - root - INFO - Successful Relocate : 10
2019-10-06 20:22:22,454 - root - INFO - Livemount Limit Wait : 5
2019-10-06 20:22:22,454 - root - INFO - Max Hosts : 5
2019-10-06 20:22:22,455 - root - INFO - Function Threads : 10
2019-10-06 20:22:22,455 - root - INFO - Thread Count : 10
2019-10-06 20:22:22,456 - root - INFO - Time Elapsed : 174.704
2019-10-06 20:22:22,456 - root - INFO - Start Time : 2019-10-06 20:18:42.717509
2019-10-06 20:22:22,459 - root - INFO - End Time : 2019-10-06 20:21:37.422251
2019-10-06 20:22:22,460 - root - INFO - Per Operation Stats for Function:
2019-10-06 20:22:22,461 - root - INFO - Median : 110.336
2019-10-06 20:22:22,461 - root - INFO - Mean : 89.851
2019-10-06 20:22:22,463 - root - INFO - Min : 35.225
2019-10-06 20:22:22,463 - root - INFO - Max : 174.161
2019-10-06 20:22:22,464 - root - INFO - Per Operation Stats for Svm:
2019-10-06 20:22:22,465 - root - INFO - Median : 44.994
2019-10-06 20:22:22,466 - root - INFO - Mean : 43.746
2019-10-06 20:22:22,468 - root - INFO - Min : 36.854
2019-10-06 20:22:22,470 - root - INFO - Max : 49.532
```

</p>
</details>



