# mass-export
## Requires
- python3
- requests
- pyvmomi

## Usage
## Running the script
```
./mass_recover.py [config_file]
```
## Looking at logs
### File Naming
```
mass_recover_20190829-191212_6_2_12.log 
mass_recover_[timestamp]_[threads]_[max_hosts]_[limit]
```

### The output
<details><summary> Expand </summary>
<p>

```
2019-08-29 19:12:54,420 - root - INFO - fileserver-002 - Export 05fe6f2d-21f4-45f3-b1bb-d7f51c3dc529 to poc-esx03.rangers.lab
2019-08-29 19:12:54,432 - root - INFO - fileserver-004 - Export 9a3a27ae-2bc7-4903-a306-4ec641a965bf to poc-esx05.rangers.lab
2019-08-29 19:12:54,448 - root - INFO - fileserver-005 - Export e419e7af-7735-4d48-a930-f83d5eac6c81 to poc-esx03.rangers.lab
2019-08-29 19:12:54,460 - root - INFO - fileserver-006 - Export f58aa17d-a980-41ec-8d6a-68dcb2dda28a to poc-esx05.rangers.lab
2019-08-29 19:12:54,475 - root - INFO - fileserver-003 - Export ebf43d9f-f6a8-427c-998d-75b98563664a to poc-esx03.rangers.lab
2019-08-29 19:12:54,682 - root - INFO - fileserver-001 - Export a4f010b0-4b16-42d4-8639-c210547185f6 to poc-esx05.rangers.lab
2019-08-29 19:12:55,567 - root - INFO - fileserver-005 - Export Status - RUNNING
2019-08-29 19:12:55,585 - root - INFO - fileserver-004 - Export Status - RUNNING
2019-08-29 19:12:55,588 - root - INFO - fileserver-006 - Export Status - RUNNING
2019-08-29 19:12:55,591 - root - INFO - fileserver-003 - Export Status - RUNNING
2019-08-29 19:12:55,595 - root - INFO - fileserver-002 - Export Status - RUNNING
2019-08-29 19:12:55,778 - root - INFO - fileserver-001 - Export Status - RUNNING
2019-08-29 19:27:05,675 - root - INFO - fileserver-001 - Export Status - SUCCEEDED
2019-08-29 19:27:05,675 - root - INFO - fileserver-001 - SUCCEEDED - cluster:::RVM15CS006261 - poc-esx05.rangers.lab - 2019-08-29T23:12:59.967Z - 2019-08-29T23:27:08.742Z
2019-08-29 19:27:11,604 - root - INFO - fileserver-007 - Export 3efdc0ca-5658-4bfd-83ad-2110565050ed to poc-esx03.rangers.lab
2019-08-29 19:27:12,714 - root - INFO - fileserver-007 - Export Status - RUNNING
2019-08-29 19:27:33,432 - root - INFO - fileserver-002 - Export Status - SUCCEEDED
2019-08-29 19:27:33,433 - root - INFO - fileserver-002 - SUCCEEDED - cluster:::RVM15CS006261 - poc-esx03.rangers.lab - 2019-08-29T23:12:59.708Z - 2019-08-29T23:27:35.108Z
2019-08-29 19:27:39,225 - root - INFO - fileserver-008 - Export 0ca82625-6344-402f-a36b-b778817954c1 to poc-esx05.rangers.lab
2019-08-29 19:27:40,380 - root - INFO - fileserver-008 - Export Status - RUNNING
2019-08-29 19:27:57,113 - root - INFO - fileserver-004 - Export Status - SUCCEEDED
2019-08-29 19:27:57,113 - root - INFO - fileserver-004 - SUCCEEDED - cluster:::RVM15CS005956 - poc-esx05.rangers.lab - 2019-08-29T23:12:59.714Z - 2019-08-29T23:28:00.672Z
2019-08-29 19:27:57,662 - root - INFO - fileserver-006 - Export Status - SUCCEEDED
2019-08-29 19:27:57,662 - root - INFO - fileserver-006 - SUCCEEDED - cluster:::RVM15CS005955 - poc-esx05.rangers.lab - 2019-08-29T23:12:59.722Z - 2019-08-29T23:27:59.420Z
2019-08-29 19:28:02,966 - root - INFO - fileserver-009 - Export c6662e93-3fcb-4cda-a88e-525eef829459 to poc-esx03.rangers.lab
2019-08-29 19:28:03,366 - root - INFO - fileserver-010 - Export 7a0e3c63-8fb0-4412-9470-294fe8355261 to poc-esx05.rangers.lab
2019-08-29 19:28:04,110 - root - INFO - fileserver-009 - Export Status - RUNNING
2019-08-29 19:28:04,454 - root - INFO - fileserver-010 - Export Status - RUNNING
2019-08-29 19:28:23,377 - root - INFO - fileserver-005 - Export Status - SUCCEEDED
2019-08-29 19:28:23,377 - root - INFO - fileserver-005 - SUCCEEDED - cluster:::RVM15CS005956 - poc-esx03.rangers.lab - 2019-08-29T23:12:59.714Z - 2019-08-29T23:28:26.249Z
2019-08-29 19:28:24,069 - root - INFO - fileserver-003 - Export Status - SUCCEEDED
2019-08-29 19:28:24,070 - root - INFO - fileserver-003 - SUCCEEDED - cluster:::RVM15CS005955 - poc-esx03.rangers.lab - 2019-08-29T23:12:59.750Z - 2019-08-29T23:28:27.057Z
2019-08-29 19:28:29,090 - root - INFO - fileserver-011 - Export ced6d49f-1d5b-4a5b-a3d2-3b235ec58054 to poc-esx03.rangers.lab
2019-08-29 19:28:29,837 - root - INFO - fileserver-012 - Export 4bbb20f1-d841-4c1a-926a-9380ab3b9ba4 to poc-esx05.rangers.lab
2019-08-29 19:28:30,247 - root - INFO - fileserver-011 - Export Status - RUNNING
2019-08-29 19:28:30,927 - root - INFO - fileserver-012 - Export Status - RUNNING
2019-08-29 19:42:49,269 - root - INFO - fileserver-007 - Export Status - SUCCEEDED
2019-08-29 19:42:49,269 - root - INFO - fileserver-007 - SUCCEEDED - cluster:::RVM15CS006048 - poc-esx03.rangers.lab - 2019-08-29T23:27:16.871Z - 2019-08-29T23:42:53.172Z
2019-08-29 19:42:59,353 - root - INFO - fileserver-008 - Export Status - SUCCEEDED
2019-08-29 19:42:59,353 - root - INFO - fileserver-008 - SUCCEEDED - cluster:::RVM15CS005955 - poc-esx05.rangers.lab - 2019-08-29T23:27:44.498Z - 2019-08-29T23:43:01.344Z
2019-08-29 19:43:32,826 - root - INFO - fileserver-010 - Export Status - SUCCEEDED
2019-08-29 19:43:32,826 - root - INFO - fileserver-010 - SUCCEEDED - cluster:::RVM15CS005955 - poc-esx05.rangers.lab - 2019-08-29T23:28:08.633Z - 2019-08-29T23:43:36.782Z
2019-08-29 19:43:39,600 - root - INFO - fileserver-009 - Export Status - SUCCEEDED
2019-08-29 19:43:39,600 - root - INFO - fileserver-009 - SUCCEEDED - cluster:::RVM15CS006261 - poc-esx03.rangers.lab - 2019-08-29T23:28:08.238Z - 2019-08-29T23:43:41.798Z
2019-08-29 19:43:58,232 - root - INFO - fileserver-011 - Export Status - SUCCEEDED
2019-08-29 19:43:58,233 - root - INFO - fileserver-011 - SUCCEEDED - cluster:::RVM15CS006261 - poc-esx03.rangers.lab - 2019-08-29T23:28:34.378Z - 2019-08-29T23:44:00.804Z
2019-08-29 19:44:02,135 - root - INFO - fileserver-012 - Export Status - SUCCEEDED
2019-08-29 19:44:02,135 - root - INFO - fileserver-012 - SUCCEEDED - cluster:::RVM15CS006261 - poc-esx05.rangers.lab - 2019-08-29T23:28:35.097Z - 2019-08-29T23:44:05.494Z
2019-08-29 19:44:05,170 - root - INFO - Snap Not Found : 0
2019-08-29 19:44:05,170 - root - INFO - Vm Not Found : 0
2019-08-29 19:44:05,170 - root - INFO - Can Be Recovered : 12
2019-08-29 19:44:05,170 - root - INFO - Successful Recovery : 12
2019-08-29 19:44:05,170 - root - INFO - Failed Recovery : 0
2019-08-29 19:44:05,170 - root - INFO - Max Hosts : 2
2019-08-29 19:44:05,171 - root - INFO - Thread Count : 6
2019-08-29 19:44:05,171 - root - INFO - Time Elapsed : 1912.677
2019-08-29 19:44:05,171 - root - INFO - Start Time : 2019-08-29 19:12:12.491921
2019-08-29 19:44:05,171 - root - INFO - End Time : 2019-08-29 19:44:05.170080
2019-08-29 19:44:05,171 - root - INFO - Recoveries Serviced cluster:::RVM15CS006261 - 5
2019-08-29 19:44:05,171 - root - INFO - Recoveries Serviced cluster:::RVM15CS005956 - 2
2019-08-29 19:44:05,171 - root - INFO - Recoveries Serviced cluster:::RVM15CS005955 - 4
2019-08-29 19:44:05,171 - root - INFO - Recoveries Serviced cluster:::RVM15CS006048 - 1
2019-08-29 19:44:05,172 - root - INFO - Recoveries Serviced poc-esx03.rangers.lab - 6
2019-08-29 19:44:05,172 - root - INFO - Recoveries Serviced poc-esx05.rangers.lab - 6
2019-08-29 19:44:17,896 - root - INFO - poc-esx03.rangers.lab - net.bytesTx.average - 164648KBps (11 points)
2019-08-29 19:44:17,999 - root - INFO - poc-esx03.rangers.lab - net.bytesRx.average - 339643KBps (11 points)
2019-08-29 19:44:18,103 - root - INFO - poc-esx03.rangers.lab - net.usage.average - 504291KBps (11 points)
2019-08-29 19:44:30,340 - root - INFO - poc-esx05.rangers.lab - net.bytesTx.average - 6707KBps (2 points)
2019-08-29 19:44:30,442 - root - INFO - poc-esx05.rangers.lab - net.bytesRx.average - 13293KBps (2 points)
2019-08-29 19:44:30,541 - root - INFO - poc-esx05.rangers.lab - net.usage.average - 20001KBps (2 points)
```

</p>
</details>

## Configuration File

```
{
  "threads": 3,
  "max_hosts": 3,
  "export": true,
  "limit": 10,
  "debug": true,
  "in_file": "in_data_full.csv",
  "prefix": "pm-test_",
  "rubrik_host": "ip/fqdn",
  "rubrik_key": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI5ZDFkYjQ2Yi1iYmEzLTRkMGItYjc5ZC01OGZiYWE4ZTgzOWIiLCJpc3MiOiJlNjY3ZWY4Yi01Y2E2LTQ1OTYtYjBhMi1jMjZjNzVhMGMzMjYiLCJqdGkiOiIxNTgyNzdlZS00M2M0LTRlODYtYjU4NC0xMzA0ZmY3OTI1ZmIifQ.9pAudx3eXYAoe9l2Y_9Qy64FldED9EeGHErE4823EAM",
  "esx_user": "root",
  "esx_pass": "supersecret"
  "omit_hosts": ["poc-esx01.rangers.lab"]
}
```
- threads (int) - number of simultaneous exports
- max_hosts (int) - number of esx hosts to export to
- export (bool) - run exports 
- limit (int) - number of line items to queue from csv
- debug (bool) - currently enables gathering of esx stats
- in_file (str) - relative path to csv
- prefix (str) - prefix for exported VMs
- rubrik_host (str) - ip/fqdn of rubrik node
- rubrik_key (str) - api token for rubrik
- esx_user (str) - esx username
- esx_pass (str) - esx password 
- omit_hosts (arr/str) - esx hosts that we don't want to export to

## .csv input file
```
Object Name,ESX Cluster,Datastore
fileserver-001,poc01-67-cluster02,PURE-DS1-10TB
fileserver-002,poc01-67-cluster02,PURE-DS1-10TB
fileserver-003,poc01-67-cluster02,PURE-DS1-10TB
fileserver-004,poc01-67-cluster02,PURE-DS1-10TB
fileserver-005,poc01-67-cluster02,PURE-DS1-10TB
fileserver-006,poc01-67-cluster02,PURE-DS1-10TB
```