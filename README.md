# mass-recovery
Allows a user to mass-recover from Rubrik and caters to various recovery types.

- Export
- Livemount
- Unmount
- Livemount with SVM (Independent queues, fails on VMware NFS limit)
- Livemount with SVM (Queued if VMware NFS limit is hit)
  
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
  "threads": 3,
  "limit": 5,
  "in_file": "in_data.csv",
  "function": 'livemount',
  "rubrik_host": "172.21.8.33",
  "rubrik_key": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI5ZDFkYjQ2Yi1iYmEzLTRkMGItYjc5ZC01OGZiYWE4ZTgzOWIiLCJpc3MiOiJlNjY3ZWY4Yi01Y2E2LTQ1OTYtYjBhMi1jMjZjNzVhMGMzMjYiLCJqdGkiOiIxNTgyNzdlZS00M2M0LTRlODYtYjU4NC0xMzA0ZmY3OTI1ZmIifQ.9pAudx3eXYAoe9l2Y_9Qy64FldED9EeGHErE4823EAM",
  "recovery_point": "2019-09-10 21:45:47",
  "show_progress": true,
  "svm": true,
  "svm_threads": 8,
  "nfs_wait": true,
  "power_on": true,
  "prefix": "pm-test_",
  "max_hosts": 3,
}
```
### Mandatory Configuration -
- threads (int) - number of simultaneous operations
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
    Note: This will show a failure in vCenter with a subsequent success.
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
2019-10-06 12:23:11,594 - root - INFO - linux-minimal-0015 - RP SUCCESS - Snap 2019-10-06T07:00:06.563Z - RP 2019-10-06 12:23:10.438478+00:00)
2019-10-06 12:23:11,731 - root - INFO - linux-minimal-0014 - RP SUCCESS - Snap 2019-10-06T07:00:04.859Z - RP 2019-10-06 12:23:10.451397+00:00)
2019-10-06 12:23:11,803 - root - INFO - linux-minimal-0020 - RP SUCCESS - Snap 2019-10-06T08:32:48.082Z - RP 2019-10-06 12:23:10.459374+00:00)
2019-10-06 12:23:11,814 - root - INFO - linux-minimal-0017 - RP SUCCESS - Snap 2019-10-06T09:16:09.424Z - RP 2019-10-06 12:23:10.453443+00:00)
2019-10-06 12:23:11,820 - root - INFO - linux-minimal-0013 - RP SUCCESS - Snap 2019-10-06T07:00:06.560Z - RP 2019-10-06 12:23:10.443418+00:00)
2019-10-06 12:23:11,836 - root - INFO - linux-minimal-0016 - RP SUCCESS - Snap 2019-10-06T07:00:08.138Z - RP 2019-10-06 12:23:10.462415+00:00)
2019-10-06 12:23:11,891 - root - INFO - linux-minimal-0021 - RP SUCCESS - Snap 2019-10-06T08:27:10.973Z - RP 2019-10-06 12:23:10.704284+00:00)
2019-10-06 12:23:11,906 - root - INFO - linux-minimal-0012 - RP SUCCESS - Snap 2019-10-06T07:00:04.831Z - RP 2019-10-06 12:23:10.699300+00:00)
2019-10-06 12:23:12,032 - root - INFO - linux-minimal-0019 - RP SUCCESS - Snap 2019-10-06T08:46:29.579Z - RP 2019-10-06 12:23:10.706279+00:00)
2019-10-06 12:23:12,052 - root - INFO - linux-minimal-0018 - RP SUCCESS - Snap 2019-10-06T07:00:04.780Z - RP 2019-10-06 12:23:10.716253+00:00)
2019-10-06 12:23:47,584 - root - INFO - linux-minimal-0014 - LM SUCCEEDED - cluster:::RVM162S009999 - 2019-10-06T16:23:10.812Z - 2019-10-06T16:23:43.375Z 
2019-10-06 12:23:58,138 - root - INFO - linux-minimal-0015 - LM SUCCEEDED - cluster:::RVM162S009991 - 2019-10-06T16:23:10.699Z - 2019-10-06T16:23:53.381Z 
2019-10-06 12:23:58,140 - root - INFO - linux-minimal-0018 - LM SUCCEEDED - cluster:::RVM162S010315 - 2019-10-06T16:23:11.164Z - 2019-10-06T16:23:49.522Z 
2019-10-06 12:23:59,492 - root - INFO - linux-minimal-0014 - SVM QUEUED to DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37
2019-10-06 12:23:59,810 - root - INFO - linux-minimal-0015 - SVM QUEUED to DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37
2019-10-06 12:23:59,825 - root - INFO - linux-minimal-0018 - SVM QUEUED to DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37
2019-10-06 12:24:01,352 - root - INFO - linux-minimal-0020 - LM SUCCEEDED - cluster:::RVM162S009999 - 2019-10-06T16:23:10.966Z - 2019-10-06T16:23:57.736Z 
2019-10-06 12:24:01,406 - root - INFO - linux-minimal-0022 - RP SUCCESS - Snap 2019-10-06T07:00:06.754Z - RP 2019-10-06 12:24:00.218605+00:00)
2019-10-06 12:24:01,710 - root - INFO - linux-minimal-0019 - LM SUCCEEDED - cluster:::RVM162S009991 - 2019-10-06T16:23:11.146Z - 2019-10-06T16:23:57.278Z 
2019-10-06 12:24:01,778 - root - INFO - linux-minimal-0024 - RP SUCCESS - Snap 2019-10-06T07:00:09.567Z - RP 2019-10-06 12:24:00.562302+00:00)
2019-10-06 12:24:01,818 - root - INFO - linux-minimal-0023 - RP SUCCESS - Snap 2019-10-06T08:24:48.843Z - RP 2019-10-06 12:24:00.502461+00:00)
2019-10-06 12:24:03,069 - root - INFO - linux-minimal-0020 - SVM QUEUED to DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37
2019-10-06 12:24:03,875 - root - INFO - linux-minimal-0019 - SVM QUEUED to DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37
2019-10-06 12:24:05,021 - root - INFO - linux-minimal-0025 - RP SUCCESS - Snap 2019-10-06T07:33:14.673Z - RP 2019-10-06 12:24:03.746458+00:00)
2019-10-06 12:24:05,701 - root - INFO - linux-minimal-0026 - RP SUCCESS - Snap 2019-10-06T09:13:03.277Z - RP 2019-10-06 12:24:04.543080+00:00)
2019-10-06 12:24:12,144 - root - INFO - linux-minimal-0021 - LM SUCCEEDED - cluster:::RVM162S010041 - 2019-10-06T16:23:11.000Z - 2019-10-06T16:24:10.020Z 
2019-10-06 12:24:12,235 - root - INFO - linux-minimal-0016 - LM SUCCEEDED - cluster:::RVM162S009991 - 2019-10-06T16:23:11.000Z - 2019-10-06T16:24:10.007Z 
2019-10-06 12:24:12,255 - root - INFO - linux-minimal-0017 - LM SUCCEEDED - cluster:::RVM162S009991 - 2019-10-06T16:23:10.923Z - 2019-10-06T16:24:07.427Z 
2019-10-06 12:24:12,265 - root - INFO - linux-minimal-0013 - LM SUCCEEDED - cluster:::RVM162S010041 - 2019-10-06T16:23:10.897Z - 2019-10-06T16:24:09.385Z 
2019-10-06 12:24:13,964 - root - INFO - linux-minimal-0016 - SVM QUEUED to DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37
2019-10-06 12:24:14,020 - root - INFO - linux-minimal-0021 - SVM QUEUED to DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37
2019-10-06 12:24:14,035 - root - INFO - linux-minimal-0013 - SVM QUEUED to DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37
2019-10-06 12:24:14,045 - root - INFO - linux-minimal-0017 - SVM QUEUED to DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37
2019-10-06 12:24:16,079 - root - INFO - linux-minimal-0029 - RP SUCCESS - Snap 2019-10-06T07:00:56.443Z - RP 2019-10-06 12:24:14.757103+00:00)
2019-10-06 12:24:16,274 - root - INFO - linux-minimal-0030 - RP SUCCESS - Snap 2019-10-06T08:49:42.167Z - RP 2019-10-06 12:24:14.956524+00:00)
2019-10-06 12:24:16,350 - root - INFO - linux-minimal-0027 - RP SUCCESS - Snap 2019-10-06T07:00:08.709Z - RP 2019-10-06 12:24:14.737111+00:00)
2019-10-06 12:24:16,500 - root - INFO - linux-minimal-0028 - RP SUCCESS - Snap 2019-10-06T07:00:10.096Z - RP 2019-10-06 12:24:14.959512+00:00)
2019-10-06 12:24:50,288 - root - INFO - linux-minimal-0024 - LM SUCCEEDED - cluster:::RVM162S009991 - 2019-10-06T16:24:00.847Z - 2019-10-06T16:24:42.590Z 
2019-10-06 12:24:51,150 - root - INFO - linux-minimal-0018 - SVM SUCCESS - to PURE-DS8-10TB
2019-10-06 12:24:52,295 - root - INFO - linux-minimal-0024 - SVM QUEUED to DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37
2019-10-06 12:24:54,548 - root - INFO - linux-minimal-0031 - RP SUCCESS - Snap 2019-10-06T07:32:22.014Z - RP 2019-10-06 12:24:53.060913+00:00)
2019-10-06 12:24:54,888 - root - INFO - linux-minimal-0014 - SVM SUCCESS - to PURE-DS8-10TB
2019-10-06 12:24:58,747 - root - INFO - linux-minimal-0020 - SVM SUCCESS - to PURE-DS8-10TB
2019-10-06 12:25:03,126 - root - INFO - linux-minimal-0028 - LM SUCCEEDED - cluster:::RVM162S009991 - 2019-10-06T16:24:15.608Z - 2019-10-06T16:25:00.566Z 
2019-10-06 12:25:08,032 - root - INFO - linux-minimal-0022 - LM SUCCEEDED - cluster:::RVM162S009999 - 2019-10-06T16:24:00.438Z - 2019-10-06T16:24:58.879Z 
2019-10-06 12:25:08,473 - root - INFO - linux-minimal-0013 - SVM SUCCESS - to PURE-DS8-10TB
2019-10-06 12:25:08,532 - root - INFO - linux-minimal-0015 - SVM SUCCESS - to PURE-DS8-10TB
2019-10-06 12:25:10,004 - root - INFO - linux-minimal-0022 - SVM QUEUED to DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37
2019-10-06 12:25:10,237 - root - INFO - linux-minimal-0028 - SVM QUEUED to DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37
2019-10-06 12:25:11,679 - root - INFO - linux-minimal-0027 - LM SUCCEEDED - cluster:::RVM162S009999 - 2019-10-06T16:24:15.510Z - 2019-10-06T16:25:07.989Z 
2019-10-06 12:25:12,296 - root - INFO - linux-minimal-0021 - SVM SUCCESS - to PURE-DS8-10TB
2019-10-06 12:25:12,316 - root - INFO - linux-minimal-0019 - SVM SUCCESS - to PURE-DS8-10TB
2019-10-06 12:25:13,557 - root - INFO - linux-minimal-0027 - SVM QUEUED to DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37
2019-10-06 12:25:15,805 - root - INFO - linux-minimal-0030 - LM SUCCEEDED - cluster:::RVM162S009991 - 2019-10-06T16:24:15.402Z - 2019-10-06T16:25:11.263Z 
2019-10-06 12:25:16,214 - root - INFO - linux-minimal-0016 - SVM SUCCESS - to PURE-DS8-10TB
2019-10-06 12:25:18,666 - root - INFO - linux-minimal-0030 - SVM QUEUED to DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37
2019-10-06 12:25:20,299 - root - ERROR - linux-minimal-0012 - LM WAIT (cluster:::RVM162S009999) - Start (2019-10-06T16:23:11.032Z) - End (2019-10-06T16:24:36.424Z)
2019-10-06 12:25:29,097 - root - INFO - linux-minimal-0031 - LM SUCCEEDED - cluster:::RVM162S010315 - 2019-10-06T16:24:53.626Z - 2019-10-06T16:25:26.873Z 
2019-10-06 12:25:36,197 - root - INFO - linux-minimal-0031 - SVM QUEUED to DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37
2019-10-06 12:25:52,485 - root - INFO - linux-minimal-0026 - LM SUCCEEDED - cluster:::RVM162S010315 - 2019-10-06T16:24:04.728Z - 2019-10-06T16:25:48.963Z 
2019-10-06 12:25:54,394 - root - INFO - linux-minimal-0017 - SVM SUCCESS - to PURE-DS8-10TB
2019-10-06 12:25:54,950 - root - INFO - linux-minimal-0026 - SVM QUEUED to DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37
2019-10-06 12:25:57,811 - root - INFO - linux-minimal-0022 - SVM SUCCESS - to PURE-DS8-10TB
2019-10-06 12:26:00,448 - root - INFO - linux-minimal-0027 - SVM SUCCESS - to PURE-DS8-10TB
2019-10-06 12:26:04,225 - root - INFO - linux-minimal-0024 - SVM SUCCESS - to PURE-DS8-10TB
2019-10-06 12:26:04,681 - root - INFO - linux-minimal-0028 - SVM SUCCESS - to PURE-DS8-10TB
2019-10-06 12:26:06,489 - root - INFO - linux-minimal-0030 - SVM SUCCESS - to PURE-DS8-10TB
2019-10-06 12:26:17,408 - root - INFO - linux-minimal-0029 - LM SUCCEEDED - cluster:::RVM162S010315 - 2019-10-06T16:24:15.188Z - 2019-10-06T16:26:13.627Z 
2019-10-06 12:26:18,793 - root - ERROR - linux-minimal-0025 - LM WAIT (cluster:::RVM162S009999) - Start (2019-10-06T16:24:04.100Z) - End (2019-10-06T16:25:43.786Z)
2019-10-06 12:26:18,801 - root - ERROR - linux-minimal-0023 - LM WAIT (cluster:::RVM162S010041) - Start (2019-10-06T16:24:00.922Z) - End (2019-10-06T16:25:44.525Z)
2019-10-06 12:26:19,258 - root - INFO - linux-minimal-0029 - SVM QUEUED to DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37
2019-10-06 12:26:27,441 - root - INFO - linux-minimal-0012 - LM SUCCEEDED - cluster:::RVM162S009991 - 2019-10-06T16:25:22.369Z - 2019-10-06T16:26:22.536Z 
2019-10-06 12:26:29,291 - root - INFO - linux-minimal-0012 - SVM QUEUED to DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37
2019-10-06 12:26:45,948 - root - INFO - linux-minimal-0031 - SVM SUCCESS - to PURE-DS8-10TB
2019-10-06 12:26:46,310 - root - INFO - linux-minimal-0026 - SVM SUCCESS - to PURE-DS8-10TB
2019-10-06 12:27:03,885 - root - INFO - linux-minimal-0023 - LM SUCCEEDED - cluster:::RVM162S009991 - 2019-10-06T16:26:20.887Z - 2019-10-06T16:26:58.758Z 
2019-10-06 12:27:05,693 - root - INFO - linux-minimal-0023 - SVM QUEUED to DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37
2019-10-06 12:27:20,376 - root - INFO - linux-minimal-0025 - LM SUCCEEDED - cluster:::RVM162S009991 - 2019-10-06T16:26:20.861Z - 2019-10-06T16:27:15.707Z 
2019-10-06 12:27:23,597 - root - INFO - linux-minimal-0029 - SVM SUCCESS - to PURE-DS8-10TB
2019-10-06 12:27:25,519 - root - INFO - linux-minimal-0025 - SVM QUEUED to DataStore:::43f24198-ace2-47b4-a441-e998812e0673-datastore-37
2019-10-06 12:27:28,294 - root - INFO - linux-minimal-0012 - SVM SUCCESS - to PURE-DS8-10TB
2019-10-06 12:28:04,893 - root - INFO - linux-minimal-0023 - SVM SUCCESS - to PURE-DS8-10TB
2019-10-06 12:28:09,407 - root - INFO - linux-minimal-0025 - SVM SUCCESS - to PURE-DS8-10TB
2019-10-06 12:28:12,410 - root - INFO - Can Be Recovered : 20
2019-10-06 12:28:12,411 - root - INFO - Successful Livemount : 20
2019-10-06 12:28:12,412 - root - INFO - Successful Relocate : 20
2019-10-06 12:28:12,414 - root - INFO - Nfs Limit Wait : 3
2019-10-06 12:28:12,415 - root - INFO - Max Hosts : 5
2019-10-06 12:28:12,416 - root - INFO - Function Threads : 10
2019-10-06 12:28:12,417 - root - INFO - Thread Count : 10
2019-10-06 12:28:12,418 - root - INFO - Time Elapsed : 257.007
2019-10-06 12:28:12,420 - root - INFO - Start Time : 2019-10-06 12:23:08.528495
2019-10-06 12:28:12,421 - root - INFO - End Time : 2019-10-06 12:27:25.535125
2019-10-06 12:28:12,425 - root - INFO - MttR - Median : 64.924
2019-10-06 12:28:12,426 - root - INFO - MttR - Mean : 84.644
2019-10-06 12:28:12,427 - root - INFO - MttR - Min : 43.894
2019-10-06 12:28:12,435 - root - INFO - MttR - Max : 202.441
```
</p>
</details>



