import requests
import sys
import time
import random
import csv
import urllib.parse
import logging
import json
import os
import traceback
import statistics
import pytz
import pprint
import urllib3
from timeit import default_timer as timer
from multiprocessing.pool import ThreadPool
from threading import Thread
from queue import Queue
from dateutil.parser import parse
from datetime import datetime
from gc import collect as gc
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

pp = pprint.PrettyPrinter(indent=4)

try:
    config = json.load(open(sys.argv[1]))
except Exception as e:
    print(e)
    exit()

if 'debug' not in config:
    config['debug'] = False

if 'limit' not in config:
    config['limit'] = 0

if 'small_timeout' not in config:
    config['small_timeout'] = 60

if 'max_livemounts' not in config:
    config['max_livemounts'] = 10

if 'detailed_audit' not in config:
    config['detailed_audit'] = False

if 'power_on' not in config:
    config['power_on'] = False

ds_filter = False

rubrik_serviced = {}
esx_serviced = {}
svm_vm = {}
timestr = time.strftime("%Y%m%d-%H%M%S")
d = "{}_{}".format(config['function_threads'], config['limit'])

kpi = {'main_thread': [], 'function_thread': [], 'svm_thread': [], 'livemount_thread': []}

vmw_file = 'cache/{}.vmw'.format(config['rubrik_host'])
ds_file = 'cache/{}.ds'.format(config['rubrik_host'])

os.makedirs('log', exist_ok=True)
logging.basicConfig(
    filename='log/mass_{}_{}_{}.log'.format(config['function'], timestr, d),
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

m = {
    "snap_not_found": 0,
    "vm_not_found": 0,
    "active_svm": 0,
    "active_exports": 0,
    "active_livemounts": 0,
    "kill_threads": 0,
    "pending_livemounts": 0,
    "can_be_recovered": 0,
    "successful_recovery": 0,
    "successful_livemounts": 0,
    "failed_livemounts": 0,
    "successful_relocate": 0,
    "nfs_limit_wait": 0,
    "livemount_limit_wait": 0,
    "nfs_limit_fail": 0,
    "successful_unmount": 0,
    "failed_operations": 0,
    "function_threads": config['function_threads']
}

start = timer()
startTime = datetime.now()

# Use Token Auth Headers
auth_header = 'Bearer ' + config['rubrik_key']
header = {'Accept': 'application/json', 'Authorization': auth_header}


# Progress Bar
def progress(current, total, summary='', supplement=''):
    bar_length = 60
    floater = int(round(bar_length * current / float(total)))
    percent = round(100.0 * current / float(total), 1)
    bar = '=' * floater + '-' * (bar_length - floater)
    if 'show_progress' in config and config['show_progress']:
        if supplement:
            sys.stdout.write('[%s] %s%s %s %s\r' % (bar, percent, '%', summary, supplement))
        else:
            sys.stdout.write('[%s] %s%s %s\r' % (bar, percent, '%', summary))
        sys.stdout.flush()
        if current == total:
            sys.stdout.flush()


# Threader
def run_threads(data, thread_count, function):
    m['thread_count'] = thread_count
    thread_pool = ThreadPool(thread_count)
    total_tasks = len(data)
    pool_instance = thread_pool.map_async(function, data, chunksize=1)
    while not pool_instance.ready():
        if 'svm' in config and config['svm']:
            summary = "Storage vMotion ({} Complete,  {} Running,  {} Queued)".format(m['successful_relocate'],
                                                                                      m['active_svm'], svm_vm.qsize())
        elif 'function' in config and config['function']== "export":
            summary = "Exports ({} Complete,  {} Running,  {} Queued)".format(total_tasks - pool_instance._number_left,
                                                                       m['active_exports'],
                                                                       pool_instance._number_left - m['active_exports'])
        else:
            summary = ''
        progress((total_tasks - pool_instance._number_left), total_tasks,
                 "({} of {})".format(total_tasks - pool_instance._number_left, total_tasks), summary)
    thread_pool.close()
    thread_pool.join()


# Main Worker Process
def run_function(vm):
    overhead_delta = 0
    try:
        thread_begin = timer()
        host_id = 0
        host_name = 0
        snap_id, cluster_name, vm_id = get_snapshot_id(vm['Object Name'])
        if config['function'] == 'unmount':
            unmount_vm(vm['Object Name'], vm_id)
            return
        if vm_id is "NOT_FOUND":
            logging.warning("{} - VM Not Found on Rubrik".format(
                vm['Object Name']))
            m['vm_not_found'] += 1
            return
        if snap_id == 'NOT_FOUND':
            logging.warning("{} - Snapshot not found for VM".format(
                vm['Object Name']))
            m['snap_not_found'] += 1
            return
        if config['function'] == 'dryrun':
            return
        if config['function'] == 'export' or (
                config['function'] == 'livemount' and 'balance_mounts' in config and config['balance_mounts']):
            if ('ESX Cluster' not in vm) or (vm['ESX Cluster'] == '') or (vm['ESX Cluster'] is None):
                vm['ESX Cluster'] = cluster_name
            if len(esx_serviced) <= (len(vm_struc[vm['ESX Cluster']]['hosts'])):
                host_name = random.choice(list(vm_struc[vm['ESX Cluster']]['hosts']))
            else:
                host_name = min(esx_serviced, key=esx_serviced.get)
            host_id = (vm_struc[vm['ESX Cluster']]['hosts'][host_name]['id'])
            if host_name not in esx_serviced:
                esx_serviced[host_name] = 1
            else:
                esx_serviced[host_name] += 1
        m['can_be_recovered'] += 1
        function_begin = timer()
        if config['function'] == 'livemount':
            svm_obj = ''
            logging.info("{} - LM QUEUED - {} to {}".format(
                vm['Object Name'], snap_id, host_name))
            try:
                mount_id, mounted_vm_id, overhead_delta = livemount_vm(vm['Object Name'], snap_id, host_id)
                svm_obj = {mount_id: {}}
            except:
                logging.error("{} - FAILED LIVEMOUNT - {} - {}".format(vm['Object Name'], snap_id, host_id))
            if 'svm' in config and config['svm']:
                ds = get_vdisk_id(vm_id)
                di = datastore_map[ds]
                logging.info("{} - SVM QUEUED - {} ({})".format(vm['Object Name'], di[1], di[0]))
                svm_obj['datastoreName'] = di[0]
                svm_obj['datastoreId'] = di[1]
                svm_obj['vmId'] = mounted_vm_id
                svm_obj['mountId'] = mount_id
                svm_obj['vmName'] = vm['Object Name']
                svm_vm.put(svm_obj)
        elif config['function'] == 'export':
            overhead_delta = 0
            di = datastore_map[get_vdisk_id(vm_id)][1]
            if di is None:
                logging.error("{} - No Datastore found in cache".format(
                    vm['Object Name']))
                m['failed_operations'] += 1
                return
            logging.info("{} - EXPORT QUEUED - {} to {} (disk {})".format(
                vm['Object Name'], snap_id, host_name, di))
            try:
                export_vm(vm['Object Name'], snap_id, host_id, di, host_name)
            except Exception as e:
                m['failed_operations'] += 1
                logging.error(e)
        thread_end = timer()
        kpi['main_thread'].append(thread_end - thread_begin)
        kpi['function_thread'].append((thread_end - function_begin) - overhead_delta)
        gc()
    except Exception as e:
        logging.exception(traceback.print_exc())


# Returns OK Rubrik Nodes IPs
def get_ips(initial_ip):
    node_ip_array = []
    endpoint = "/api/internal/node"
    uri = ("https://{}{}".format(initial_ip, endpoint))
    pp.pprint(uri)
    response = requests.get(uri, headers=header, verify=False, timeout=config['small_timeout'])
    if response.status_code >= 400:
        raise SystemExit('Authentication to {} failed, please check your API Token'.format(initial_ip))
    response = response.json()
    for node in response['data']:
        if node['status'] == "OK":
            node_ip_array.append("https://{}".format(node['ipAddress']))
    return node_ip_array


# zips csv file into a keyed dictionary
def get_csv_data(file_name):
    read_file = csv.DictReader(open(file_name))
    return [dict(line) for line in read_file]


# Produces the virtual infrastructure layout as provided by Rubrik Metadata
def get_vm_structure():
    os.makedirs('cache', exist_ok=True)
    try:
        with open(vmw_file) as j:
            infra_data = json.load(j)
    except FileNotFoundError:
        infra_data = {}
        endpoint = "/api/v1/vmware/compute_cluster"
        uri = ("{}{}?limit=999&primary_cluster_id=local".format(
            random.choice(node_ips), endpoint))
        response = requests.get(uri, headers=header, verify=False,
                                timeout=30).json()
        for response in response['data']:
            infra_data[response['name']] = {'id': response['id']}
            call = "/api/v1/vmware/compute_cluster"
            uri = ("{}{}/{}".format(random.choice(node_ips), call,
                                    response['id']))
            request = requests.get(uri,
                                   headers=header,
                                   verify=False,
                                   timeout=60).json()
            infra_data[response['name']]['hosts'] = {}
            host_count = 0
            for response_details in request['hosts']:
                if 'omit_hosts' in config and response_details['name'] in config['omit_hosts']:
                    continue
                if 'max_hosts' in config and host_count == config['max_hosts']:
                    continue
                host_count += 1
                infra_data[response['name']]['hosts'][response_details['name']] = {
                    'id': response_details['id']
                }
                infra_data[response['name']]['hosts'][
                    response_details['name']]['datastores'] = {}
                call = "/api/v1/vmware/host"
                uri = ("{}{}/{}".format(random.choice(node_ips), call,
                                        response_details['id']))
                request = requests.get(uri,
                                       headers=header,
                                       verify=False,
                                       timeout=config['small_timeout']).json()
                for response_datastores in request['datastores']:
                    infra_data[response['name']]['hosts'][
                        response_details['name']]['datastores'][
                        response_datastores['name']] = {
                        'id': response_datastores['id']
                    }
        with open(vmw_file, 'w') as o:
            json.dump(infra_data, o, indent=4, sort_keys=True)
    return infra_data


# Returns the first virtual disk ID for a virtual machine
def get_vdisk_id(vm_id):
    endpoint = "/api/v1/vmware/vm/"
    uri = ("{}{}{}".format(random.choice(node_ips), endpoint, urllib.parse.quote(vm_id)))
    response = requests.get(uri, headers=header, verify=False, timeout=config['small_timeout']).json()
    return response['virtualDiskIds'][0]


# Produces a map of virtual machines to datastore as provided by Rubrik Metadata
def get_datastore_map():
    os.makedirs('cache', exist_ok=True)
    try:
        with open(ds_file) as j:
            datastore_info = json.load(j)
    except FileNotFoundError:
        datastore_info = {}
        endpoint = "/api/internal/vmware/datastore"
        uri = ("{}{}".format(random.choice(node_ips), endpoint))
        response = requests.get(uri, headers=header, verify=False, timeout=60).json()
        for datastore in response['data']:
            if ds_filter:
                if "PURE" not in datastore['name']:
                    continue
            print("Getting for {} ".format(datastore['name']), end='')
            endpoint = "/api/internal/vmware/datastore/"
            uri = ("{}{}{}".format(random.choice(node_ips), endpoint, datastore['id']))
            response = requests.get(uri, headers=header, verify=False, timeout=90).json()
            if 'virtualDisks' in response:
                for virtual_disk in response['virtualDisks']:
                    print('.', end='')
                    if virtual_disk['id'] not in datastore_info:
                        datastore_info[virtual_disk['id']] = [datastore['name'], datastore['id']]
            print("Done")
        with open(ds_file, 'w') as o:
            json.dump(datastore_info, o, indent=4, sort_keys=True)
    return datastore_info


def livemount_table():
    livemount_data = {}
    endpoint = "/api/v1/vmware/vm/snapshot/mount"
    uri = ("{}{}?limit=9999".format(random.choice(node_ips), endpoint))
    response = requests.get(uri, headers=header, verify=False, timeout=config['small_timeout']).json()
    for response in response['data']:
        if response['vmId'] not in livemount_data:
            livemount_data[response['vmId']] = []
        livemount_data[response['vmId']].append(response['id'])
    return livemount_data


def unmount_vm(v, vi):
    c = "/api/v1/vmware/vm/snapshot/mount/"
    if vi in lmt:
        for si in lmt[vi]:
            u = ("{}{}{}".format(random.choice(node_ips), c, si))
            logging.info("{} - UNMOUNT - {} - {}".format(v, vi, si))
            m['successful_unmount'] += 1
            requests.delete(u, headers=header, verify=False, timeout=config['small_timeout']).json()
    return


def relocate_vm(input_queue):
    svm_started = False
    while True:
        time.sleep(3)
        # Clean up if this is the last thread to be run
        if svm_started and not input_queue.qsize() and not m['active_livemounts'] and not m['pending_livemounts']:
            sys.exit()
        svm_object = dict(input_queue.get())
        svm_start = timer()
        try:
            svm_started = True
            endpoint = "/api/v1/vmware/vm/snapshot/mount"
            payload = {
                "datastoreId": svm_object['datastoreId']
            }
            uri = ("{}{}/{}/relocate".format(random.choice(node_ips), endpoint, svm_object['mountId']))
            response = requests.post(uri, json=payload, headers=header, verify=False, timeout=60).json()
            request_id = response['id']
            this_svm_complete = False
            m['active_svm'] += 1
            logging.info(
                "{} - SVM RUNNING - {} ({})".format(svm_object['vmName'], svm_object['datastoreName'],
                                                    svm_object['datastoreId']))
            while not this_svm_complete:
                time.sleep(3)
                try:
                    endpoint = "/api/internal/event"
                    uri = ("{}{}?object_ids={}".format(random.choice(node_ips), endpoint, svm_object['vmId']))
                    response = requests.get(uri, headers=header, verify=False, timeout=config['small_timeout']).json()
                    for result in response['data']:
                        if request_id == result['jobInstanceId']:
                            if result['eventStatus'] == "Success":
                                logging.info(
                                    "{} - SVM SUCCEED - {} ({})".format(svm_object['vmName'],
                                                                        svm_object['datastoreName'],
                                                                        svm_object['datastoreId']))
                                m['successful_relocate'] += 1
                                m['active_livemounts'] -= 1
                                this_svm_complete = True
                            elif "FAIL" in result['eventStatus']:
                                logging.error(
                                    "{} - SVM FAIL - {} ({})".format(svm_object['vmName'], svm_object['datastoreName'],
                                                                     svm_object['datastoreId']))
                                m['failed_relocate'] += 1
                                this_svm_complete = True
                            if 'detailed_audit' in config and config['detailed_audit'] and this_svm_complete:
                                endpoint = "/api/internal/event_series"
                                uri = ("{}{}/{}".format(random.choice(node_ips), endpoint, result['eventSeriesId']))
                                response = requests.get(uri, headers=header, verify=False,
                                                        timeout=config['small_timeout']).json()
                                for event_detail in response['eventDetailList']:
                                    event_info = json.loads(event_detail['eventInfo'])
                                    logging.info("{} - SVM AUDIT - {} - {}".format(
                                        svm_object['vmName'], event_detail['time'], event_info['message']))
                except Exception as e:
                    logging.error(traceback.print_exc())
                    m['active_svm'] -= 1
                    continue
        except Exception as e:
            logging.error(traceback.print_exc())
            m['active_svm'] -= 1
            continue
        svm_end = timer()
        kpi['svm_thread'].append(svm_end - svm_start)
        m['active_svm'] -= 1
        continue


def livemount_vm(vm_name, snapshot_id, host_id=''):
    lm_queued = False
    lm_active = False
    while not lm_active:
        time.sleep(3)
        # Queue the livemount if config['max_livemounts'] is hit
        if (m['active_livemounts'] >= config['max_livemounts']) and not lm_queued:
            lm_queued = True
            m['livemount_limit_wait'] += 1
            m['pending_livemounts'] += 1
        # Perform the livemount if a spot is open
        elif m['active_livemounts'] < config['max_livemounts']:
            livemount_start = timer()
            endpoint = "/api/v1/vmware/vm/snapshot"
            payload = {
                "disableNetwork": True,
                "removeNetworkDevices": False,
                "powerOn": config['power_on'],
            }
            # Set the recovery ESX host if defined
            if host_id:
                payload['hostId'] = host_id
            # Set the vm_name prefix if defined
            if 'prefix' in config:
                payload['vmName'] = "{}{}".format(config['prefix'], vm_name)
            uri = ("{}{}/{}/mount".format(random.choice(node_ips), endpoint, snapshot_id))
            response = requests.post(uri, json=payload, headers=header, verify=False,
                                     timeout=config['small_timeout']).json()
            request_id = response['id']
            lm_complete = False
            lm_failed = False
            while not lm_complete:
                time.sleep(3)
                endpoint = "/api/v1/vmware/vm/request"
                uri = ("{}{}/{}".format(random.choice(node_ips), endpoint, request_id))
                response = requests.get(uri, headers=header, verify=False, timeout=60).json()
                if response['status'] == "SUCCEEDED":
                    m['active_livemounts'] += 1
                    # Keep a tally of which Rubrik Nodes service requests
                    if response['nodeId'] not in rubrik_serviced:
                        rubrik_serviced[response['nodeId']] = 1
                    else:
                        rubrik_serviced[response['nodeId']] += 1
                    if lm_queued:
                        m['pending_livemounts'] -= 1
                    m['successful_livemounts'] += 1
                    lm_complete = True
                    lm_active = True
                    logging.info("{} - LM {} - {} - {} - {} - {}".format(
                        vm_name, response['status'], response['nodeId'], response['startTime'], response['endTime'],
                        (parse(response['endTime']) - parse(response['startTime']))))
                    for returned_links in response['links']:
                        overhead_delta = 0
                        if returned_links['rel'] == 'result':
                            request_detail = requests.get(returned_links['href'], headers=header, verify=False,
                                                          timeout=config['small_timeout']).json()
                            # Grabs portions of event log of interest
                            if 'detailed_audit' in config and config['detailed_audit']:
                                overhead_begin = timer()
                                endpoint = "/api/internal/event"
                                uri = ("{}{}?limit=20&status=Success&event_type=Recovery&object_ids={}".format(
                                    random.choice(node_ips), endpoint, request_detail['vmId']))
                                response = requests.get(uri, headers=header, verify=False,
                                                        timeout=config['small_timeout']).json()
                                for event_data in response['data']:
                                    if event_data['jobInstanceId'] == request_id:
                                        endpoint = "/api/internal/event_series"
                                        uri = ("{}{}/{}".format(random.choice(node_ips), endpoint,
                                                                event_data['eventSeriesId']))
                                        response = requests.get(uri, headers=header, verify=False,
                                                                timeout=config['small_timeout']).json()
                                        for event_detail in response['eventDetailList']:
                                            event_info = json.loads(event_detail['eventInfo'])
                                            logging.info("{} - LM AUDIT - {} - {}".format(
                                                vm_name, event_detail['time'], event_info['message']))
                                overhead_delta = (timer() - overhead_begin)
                            livemount_end = timer()
                            kpi['livemount_thread'].append(livemount_end - livemount_start)
                            return request_detail['id'], request_detail['mountedVmId'], overhead_delta
                if response['status'] == 'FAILED':
                    if 'Failed to create NAS datastore' in json.dumps(response['error']):
                        if 'nfs_wait' in config and config['nfs_wait']:
                            response['status'] = "WAIT"
                            m['nfs_limit_wait'] += 1
                            time.sleep(30)
                            lm_active = False
                        else:
                            m['nfs_limit_fail'] += 1
                            lm_active = True
                    else:
                        m['failed_livemounts'] += 1
                        lm_complete = True
                        lm_failed = True
                    logging.error(
                        "{} - LM {} ({}) - Start ({}) - End ({})".
                            format(vm_name, response['status'], response['nodeId'], response['startTime'],
                                   response['endTime']))
                    logging.error(response['error']['message'])
                    if lm_failed:
                        return 0
    return 0


def export_vm(vm_name, snapshot_id, host_id, datastore_id, host_name):
    try:
        endpoint = "/api/v1/vmware/vm/snapshot"
        payload = {
            "disableNetwork": False,
            "removeNetworkDevices": False,
            "powerOn": config['power_on'],
            "keepMacAddresses": True,
            "hostId": "{}".format(host_id),
            "datastoreId": "{}".format(datastore_id),
            "unregisterVm": False,
            "shouldRecoverTags": True
        }
        if 'prefix' in config:
            payload['vmName'] = "{}{}".format(config['prefix'], vm_name)
        else:
            payload['vmName'] = "{}".format(vm_name)
        uri = ("{}{}/{}/export".format(random.choice(node_ips), endpoint, snapshot_id))
        response = requests.post(uri, json=payload, headers=header, verify=False,
                                 timeout=config['small_timeout']).json()
        request_id = response['id']
        export_complete = False
        m['active_exports'] += 1
        while not export_complete:
            endpoint = "/api/v1/vmware/vm/request"
            uri = ("{}{}/{}".format(random.choice(node_ips), endpoint, request_id))
            response = requests.get(uri, headers=header, verify=False, timeout=config['small_timeout']).json()
            ls = response['status']
            if ls == "SUCCEEDED":
                logging.info("{} - EXPORT SUCCEED - {} - {} - {} - {}".format(
                    vm_name, response['nodeId'], host_name, response['startTime'], response['endTime']))
                if response['nodeId'] not in rubrik_serviced:
                    rubrik_serviced[response['nodeId']] = 1
                else:
                    rubrik_serviced[response['nodeId']] += 1
                m['successful_recovery'] += 1
                export_complete = True
                m['active_exports'] -= 1
            if "FAIL" in ls:
                logging.error(
                    "{} - Export FAIL - {} - Start ({}) - End ({})".format(
                        vm_name, response['nodeId'], response['startTime'], response['endTime']))
                logging.error(response['error'])
                m['failed_operations'] += 1
                m['active_exports'] -= 1
                export_complete = True
            time.sleep(3)
        return
    except Exception as e:
        logging.error(traceback.print_exc())
        m['active_exports'] -= 1
        return


# Returns latest snap_id from vm_id - if config['recovery_point'] then find closest to time without going over
# 2019-09-15T07:02:54.470Z
def get_snapshot_id(vm_name):
    snapshot_date_comparison = {}
    if 'recovery_point' in config:
        recovery_point = pytz.utc.localize(parse(config['recovery_point']))
    else:
        recovery_point = pytz.utc.localize(datetime.now())
    endpoint = "/api/v1/vmware/vm"
    uri = ("{}{}?primary_cluster_id=local&name={}".format(random.choice(node_ips), endpoint,
                                                                         urllib.parse.quote(vm_name)))
    res = requests.get(uri, headers=header, verify=False, timeout=config['small_timeout']).json()
    if res['total'] < 1:
        return '','','NOT_FOUND'
    for vm_response in res['data']:
        if vm_response['name'] == vm_name:
            endpoint = "/api/v1/vmware/vm/"
            uri = ("{}{}{}".format(random.choice(node_ips), endpoint, urllib.parse.quote(vm_response['id'])))
            response = requests.get(uri, headers=header, verify=False, timeout=config['small_timeout']).json()
            if response['snapshotCount'] > 0:
                for snap in response['snapshots']:
                    snapshot_date = parse(snap['date'])
                    if recovery_point > snapshot_date:
                        delta = abs(recovery_point - snapshot_date)
                        snapshot_date_comparison[delta] = {}
                        snapshot_date_comparison[delta]['id'] = snap['id']
                        snapshot_date_comparison[delta]['vm_id'] = vm_response['id']
                        snapshot_date_comparison[delta]['vm_name'] = vm_response['name']
                        snapshot_date_comparison[delta]['dt'] = snap['date']
                        try:
                            snapshot_date_comparison[delta]['cn'] = vm_response['clusterName']
                        except:
                            snapshot_date_comparison[delta]['cn'] = ''
            else:
                return 'NOT_FOUND', vm_response['clusterName'], vm_response['id']
    if snapshot_date_comparison:
        closest_snapshot_date = min(snapshot_date_comparison)
    else:
        return
    logging.info(
        "{} - RP SUCCEED - Snap {} - RP {}".format(snapshot_date_comparison[closest_snapshot_date]['vm_name'],
                                                   snapshot_date_comparison[closest_snapshot_date]['dt'],
                                                   recovery_point))
    return snapshot_date_comparison[closest_snapshot_date]['id'],  \
           snapshot_date_comparison[closest_snapshot_date]['cn'], \
           snapshot_date_comparison[closest_snapshot_date]['vm_id']


# Dumps some useful metrics at the end.
def print_m(m):
    print("\n Job Statistics:")
    for i in m:
        if m[i] != 0:
            print("\t {} : {}".format(i.replace('_', ' ').title(), m[i]))
            logging.info("{} : {}".format(i.replace('_', ' ').title(), m[i]))
    for topic in kpi:
        if kpi[topic]:
            c = {'median': round(statistics.median_high(kpi[topic]), 3),
                 'mean': round(statistics.mean(kpi[topic]), 3),
                 'min': round(min(kpi[topic]), 3),
                 'max': round(max(kpi[topic]), 3)}
            print("Per Operation Stats for {}:".format(topic.replace('_', ' ').title()))
            logging.info("Per Operation Stats for {}:".format(topic.replace('_', ' ').title()))
            for o in c:
                print("\t {} : {}".format(o.title(), c[o]))
                logging.info("{} : {}".format(o.title(), c[o]))


if __name__ == '__main__':
    if 'small_timeout' not in config:
        config['small_timeout'] = 30
    # Get Rubrik Nodes so we can thread against them
    print("Getting Rubrik Node Information", end='')
    node_ips = get_ips(config['rubrik_host'])
    print(" - Done")

    # Get VMware structure so that we can round robin
    if config['function'] == 'export' or config['function'] == 'livemount':
        print("Getting VMware Structures", end='')
        vm_struc = get_vm_structure()
        print(" - Done")

        # Get datastore map
        print("Getting Datastore Map", end='')
        datastore_map = get_datastore_map()
        print(" - Done")

    if config['function'] == 'unmount':
        lmt = livemount_table()

    # Grab recovery info from csv
    print("Getting Recovery Data", end='')
    data = get_csv_data(config['in_file'])
    if config['limit'] > 0:
        data = data[0:config['limit']]
    print(" - Done")

    if 'livemount' not in config['function']:
        config['svm'] = False

    # start the svm processor
    svm_threads = []
    if 'svm' in config and config['svm']:
        svm_vm = Queue()
        if len(data) < config['svm_threads']:
            config['svm_threads'] = len(data)
        for i in range(config['svm_threads']):
            svm_process = Thread(target=relocate_vm, args=(svm_vm,))
            svm_threads.append(svm_process)
            svm_process.setDaemon(True)
            svm_process.start()

    print("Running {}".format(config['function'].title()))
    run_threads(data, config['function_threads'], run_function)
    end = timer()
    progress(len(data), len(data),
             "Completed in {} seconds                                              ".format(round(end - start, 3)))
    m['function_elapsed'] = round(end - start, 3)
    m['function_start_time'] = startTime
    endTime = datetime.now()
    m['function_end_time'] = endTime
    print('')

    # Show output for the remaining SVMs, and clean it all up.
    if 'svm' in config and config['svm']:
        while True:
            s = "Storage vMotion: ({} Complete,  {} Running,  {} Queued) Livemounts Active: {}       ".format(
                m['successful_relocate'], m['active_svm'], svm_vm.qsize(), m['active_livemounts'])
            sys.stdout.write(s + "\r")
            sys.stdout.flush()
            if m['active_svm'] or m['active_livemounts'] or m['pending_livemounts'] or svm_vm.qsize():
                time.sleep(3)
            else:
                break
        for svm_thread in svm_threads:
            svm_thread.join(0)
        print()
        endTime = datetime.now()
        end = timer()
        m['svm_elapsed'] = round(end - start, 3)
        m['svm_end_time'] = endTime

    print_m(m)

    for i in rubrik_serviced:
        logging.info("Recoveries Serviced {} - {}".format(i, rubrik_serviced[i]))

    for i in esx_serviced:
        logging.info("Recoveries Serviced {} - {}".format(i, esx_serviced[i]))

    exit()
