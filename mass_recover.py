import requests
import sys
import time
import random
import csv
import urllib.parse
import logging
import json
import os
import statistics
import pytz
from timeit import default_timer as timer
from multiprocessing.pool import ThreadPool
from threading import Thread
import threading
from queue import Queue
from dateutil.parser import parse
from datetime import datetime
from gc import collect as gc
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    config = json.load(open(sys.argv[1]))
except Exception as e:
    print(e)
    exit()


if 'debug' not in config:
    config['debug'] = False

if 'max_hosts' not in config:
    config['max_hosts'] = 0

if 'limit' not in config:
    config['limit'] = 0

if 'power_on' not in config:
    config['power_on'] = False
else:
    config['power_on'] = True

sla = "Bronze"
rn = {}
svm_vm = {}
timestr = time.strftime("%Y%m%d-%H%M%S")
d = "{}_{}_{}".format(config['function_threads'], config['max_hosts'], config['limit'])

kpi_function = []
kpi_svm = []

vmw_file = 'cache/{}.vmw'.format(config['rubrik_host'])
ds_file = 'cache/{}.ds'.format(config['rubrik_host'])

os.makedirs('log', exist_ok=True)
logging.basicConfig(
    filename='log/mass_{}_{}_{}.log'.format(config['function'], timestr, d),
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

#track = {}

m = {
    "snap_not_found": 0,
    "vm_not_found": 0,
    "active_svm": 0,
    "can_be_recovered": 0,
    "successful_recovery": 0,
    "successful_livemount": 0,
    "successful_relocate": 0,
    "nfs_limit_wait": 0,
    "nfs_limit_fail": 0,
    "successful_unmount": 0,
    "failed_operations": 0,
    "max_hosts": config['max_hosts'],
    "function_threads": config['function_threads']
}

recoveries = {}

start = timer()
startTime = datetime.now()

# Use Token Auth Headers
auth_header = 'Bearer ' + config['rubrik_key']
header = {'Accept': 'application/json', 'Authorization': auth_header}


# Progress Bar
def progress(c, t, s='', sl=''):
    bl = 60
    fl = int(round(bl * c / float(t)))
    p = round(100.0 * c / float(t), 1)
    b = '=' * fl + '-' * (bl - fl)
    if 'show_progress' in config and config['show_progress']:
        if sl:
            sys.stdout.write('[%s] %s%s %s %s\r' % (b, p, '%', s, sl))
        else:
            sys.stdout.write('[%s] %s%s %s\r' % (b, p, '%', s))
        sys.stdout.flush()
        if c == t:
            sys.stdout.flush()


# Threader
def run_threads(v, t, f):
    m['thread_count'] = t
    p = ThreadPool(t)
    t = len(v)
    r = p.map_async(f, v, chunksize=1)
    while not r.ready():
        if config['svm']:
            s = "Storage vMotion ({} Complete,  {} Running,  {} Queued)".format(m['successful_relocate'], m['active_svm'], svm_vm.qsize())
        progress((t - r._number_left), t, "({} of {})".format(t - r._number_left, t ), s)
    p.close()
    p.join()


# Main Worker Process
def run_function(vm):
    b = timer()
    vid = get_vm_id(vm['Object Name'])
    if vid is None:
        logging.warning("{} - VM Not Found on Rubrik".format(
            vm['Object Name']))
        m['vm_not_found'] += 1
        return
    si, vi = get_snapshot_id(vid)
    hs = vid[vi]
    if si is None:
        logging.warning("{} - Snapshot not found for VM".format(
            vm['Object Name']))
        m['snap_not_found'] += 1
        return
    if config['function'] == 'dryrun':
        return
    m['can_be_recovered'] += 1
    if config['function'] == 'livemount':
        mount_id, mounted_vm_id = livemount_vm(vm['Object Name'], si)
        svm_obj = {mount_id: {}}
        if config['svm']:
            ds = get_vdisk_id(vi)
            di = datastore_map[ds]
            logging.info("{} - SVM QUEUED to {}".format(vm['Object Name'], di[1]))
            svm_obj['datastoreName'] = di[0]
            svm_obj['datastoreId'] = di[1]
            svm_obj['vmId'] = mounted_vm_id
            svm_obj['mountId'] = mount_id
            svm_obj['vmName'] = vm['Object Name']
            svm_vm.put(svm_obj)
    elif config['function'] == 'unmount':
        unmount_vm(vm['Object Name'], vi)
    elif config['function'] == 'export':
        if ('ESX Cluster' not in vm) or (vm['ESX Cluster'] == '') or (vm['ESX Cluster'] is None):
            vm['ESX Cluster'] = hs
        if len(recoveries) <= (config['max_hosts'] - 1):
            h = random.choice(list(vm_struc[vm['ESX Cluster']]['hosts']))
        else:
            h = min(recoveries, key=recoveries.get)
        di = datastore_map[get_vdisk_id(vi)][1]
        if di is None:
            logging.error("{} - No Datastore found in cache".format(
                vm['Object Name']))
            m['failed_operations'] += 1
            return
        logging.info("{} - EXPORT {} to {} (disk {})".format(
            vm['Object Name'], si, h, di))
        hi = (vm_struc[vm['ESX Cluster']]['hosts'][h]['id'])
        if h not in recoveries:
            recoveries[h] = 1
        else:
            recoveries[h] += 1
        try:
            export_vm(vm['Object Name'], si, hi, di, h)
        except Exception as e:
            m['failed_operations'] += 1
            logging.error(e)
            print("Export failed - " + e)
    f = timer()
    kpi_function.append(f - b)
    gc()


# Returns OK Rubrik Nodes
def get_ips(i):
    o = []
    c = "/api/internal/node"
    u = ("https://{}{}".format(i, c))
    r = requests.get(u, headers=header, verify=False, timeout=15).json()
    for n in r['data']:
        if n['status'] == "OK":
            o.append("https://{}".format(n['ipAddress']))
    return o


# zips csv file into a keyed dictionary
def get_csv_data(f):
    reader = csv.DictReader(open(f))
    return [dict(r) for r in reader]


# Get Datastore DICT
def get_vm_structure():
    os.makedirs('cache', exist_ok=True)
    try:
        with open(vmw_file) as j:
            h = json.load(j)
    except FileNotFoundError:
        h = {}
        call = "/api/v1/vmware/compute_cluster"
        uri = ("{}{}?limit=999&primary_cluster_id=local".format(
            random.choice(node_ips), call))
        request = requests.get(uri, headers=header, verify=False,
                               timeout=30).json()
        for response in request['data']:
            h[response['name']] = {'id': response['id']}
            call = "/api/v1/vmware/compute_cluster"
            uri = ("{}{}/{}".format(random.choice(node_ips), call,
                                    response['id']))
            request = requests.get(uri,
                                   headers=header,
                                   verify=False,
                                   timeout=60).json()
            h[response['name']]['hosts'] = {}
            hc = 0
            for response_details in request['hosts']:
                if 'omit_hosts' in config and response_details['name'] in config['omit_hosts']:
                    continue
                if hc == config['max_hosts']:
                    continue
                hc += 1
                h[response['name']]['hosts'][response_details['name']] = {
                    'id': response_details['id']
                }
                h[response['name']]['hosts'][
                    response_details['name']]['datastores'] = {}
                call = "/api/v1/vmware/host"
                uri = ("{}{}/{}".format(random.choice(node_ips), call,
                                        response_details['id']))
                request = requests.get(uri,
                                       headers=header,
                                       verify=False,
                                       timeout=15).json()
                for response_datastores in request['datastores']:
                    h[response['name']]['hosts'][
                        response_details['name']]['datastores'][
                        response_datastores['name']] = {
                        'id': response_datastores['id']
                    }
        with open(vmw_file, 'w') as o:
            json.dump(h, o)
    return h


# Grab the Datastore name from the VM Record
def get_vdisk_id(v):
    c = "/api/v1/vmware/vm/"
    u = ("{}{}{}".format(random.choice(node_ips), c, urllib.parse.quote(v)))
    r = requests.get(u, headers=header, verify=False, timeout=15).json()
    return r['virtualDiskIds'][0]


# Grab the Datastore name from the VM Record
def get_datastore_map():
    os.makedirs('cache', exist_ok=True)
    try:
        with open(ds_file) as j:
            dsm = json.load(j)
    except FileNotFoundError:
        dsm = {}
        c = "/api/internal/vmware/datastore"
        u = ("{}{}".format(random.choice(node_ips), c))
        r = requests.get(u, headers=header, verify=False, timeout=60).json()
        for z in r['data']:
            if "PURE" not in z['name']:
                continue
            print("Getting for {} ".format(z['name']), end='')
            cc = "/api/internal/vmware/datastore/"
            uu = ("{}{}{}".format(random.choice(node_ips), cc, z['id']))
            rr = requests.get(uu, headers=header, verify=False,
                              timeout=90).json()
            if 'virtualDisks' in rr:
                for vd in rr['virtualDisks']:
                    print('.', end='')
                    if vd['id'] not in dsm:
                        dsm[vd['id']] = [z['name'], z['id']]
            print("Done")
        with open(ds_file, 'w') as o:
            json.dump(dsm, o)
    return dsm


# Returns vm_id from vm_name
def get_vm_id(v):
    c = "/api/v1/vmware/vm"
    u = ("{}{}?name={}".format(random.choice(node_ips), c,
                               urllib.parse.quote(v)))
    r = requests.get(u, headers=header, verify=False, timeout=15).json()
    o = {}
    for response in r['data']:
        if response['name'] == v:
            o[response['id']] = response['clusterName']
    return o


def livemount_table():
    o = {}
    c = "/api/v1/vmware/vm/snapshot/mount"
    u = ("{}{}?limit=9999".format(random.choice(node_ips), c))
    r = requests.get(u, headers=header, verify=False, timeout=15).json()
    for response in r['data']:
        if response['vmId'] not in o:
            o[response['vmId']] = []
        o[response['vmId']].append(response['id'])
    return o


def unmount_vm(v, vi):
    c = "/api/v1/vmware/vm/snapshot/mount/"
    if vi in lmt:
        for si in lmt[vi]:
            u = ("{}{}{}".format(random.choice(node_ips), c, si))
            logging.info("{} - UNMOUNT - {} - {}".format(v, vi, si))
            m['successful_unmount'] += 1
            requests.delete(u, headers=header, verify=False, timeout=15).json()
    return


def relocate_vm(vm):
    run = True
    while run:
        svm_object = dict(vm.get(block=True))
        svm_start = timer()
        try:
            c = "/api/v1/vmware/vm/snapshot/mount"
            lo = {
                "datastoreId": svm_object['datastoreId']
            }
            u = ("{}{}/{}/relocate".format(random.choice(node_ips), c, svm_object['mountId']))
            r = requests.post(u, json=lo, headers=header, verify=False, timeout=15).json()
            t = r['id']
            s = False
            m['active_svm'] += 1
            while not s:
                try:
                    c = "/api/internal/event"
                    u = ("{}{}?object_ids={}".format(random.choice(node_ips), c, svm_object['vmId']))
                    r = requests.get(u, headers=header, verify=False, timeout=15).json()
                    for result in r['data']:
                        if t == result['jobInstanceId']:
                            if result['eventStatus'] == "Success":
                                logging.info(
                                    "{} - SVM SUCCEED - to {}".format(svm_object['vmName'], svm_object['datastoreName']))
                                m['successful_relocate'] += 1
                                s = True
                            elif "Fail" in result['eventStatus']:
                                logging.error(
                                    "{} - SVM FAIL {} to {}".format(svm_object['vmName'], svm_object['datastoreName']))
                                m['failed_relocate'] += 1
                                s = True
                    time.sleep(3)
                except Exception as e:
                    print(e)
            if svm_vm.empty():
                run = False
        except Exception as e:
            print(e)
        svm_end = timer()
        kpi_svm.append(svm_end - svm_start)
        m['active_svm'] -= 1


def livemount_vm(v, si):
    complete = False
    while not complete:
        c = "/api/v1/vmware/vm/snapshot"
        lo = {
            "disableNetwork": True,
            "removeNetworkDevices": False,
            "powerOn": config['power_on'],
        }
        u = ("{}{}/{}/mount".format(random.choice(node_ips), c, si))
        r = requests.post(u, json=lo, headers=header, verify=False,
                          timeout=15).json()
        t = r['id']
        s = False
        while not s:
            c = "/api/v1/vmware/vm/request"
            u = ("{}{}/{}".format(random.choice(node_ips), c, t))
            r = requests.get(u, headers=header, verify=False, timeout=15).json()
            ls = r['status']
            if ls == "SUCCEEDED":
                logging.info("{} - LM {} - {} - {} - {} ".format(
                    v, r['status'], r['nodeId'], r['startTime'], r['endTime']))
                m['successful_livemount'] += 1
                if config['svm']:
                    for i in r['links']:
                        if i['rel'] == 'result':
                            o = requests.get(i['href'], headers=header, verify=False, timeout=15).json()
                            return o['id'], o['mountedVmId']
                s = True
                return 1
            if "FAIL" in ls:
                if 'Failed to create NAS datastore' in json.dumps(r['error']):
                    if config['nfs_wait']:
                        complete = False
                        r['status'] = "WAIT"
                        m['nfs_limit_wait'] += 1
                        time.sleep(30)
                    else:
                        complete = True
                        m['nfs_limit_fail'] += 1
                else:
                    m['failed_operations'] += 1
                    logging.error(r['error'])
                    complete = True
                logging.error(
                    "{} - LM {} ({}) - Start ({}) - End ({})".
                        format(v, r['status'], r['nodeId'], r['startTime'],
                               r['endTime']))
                s = True
            time.sleep(3)
    return 0


def export_vm(v, si, hi, di, h):
    print("In Export")
    c = "/api/v1/vmware/vm/snapshot"
    lo = {
        "disableNetwork": False,
        "removeNetworkDevices": False,
        "powerOn": config['power_on'],
        "keepMacAddresses": True,
        "hostId": "{}".format(hi),
        "datastoreId": "{}".format(di),
        "unregisterVm": False,
        "shouldRecoverTags": True
    }
    if 'prefix' in config:
        lo['vmName'] = "{}{}".format(config['prefix'], v)
    else:
        lo['vmName'] = "{}".format(v)
    u = ("{}{}/{}/export".format(random.choice(node_ips), c, si))
    r = requests.post(u, json=lo, headers=header, verify=False,
                      timeout=15).json()
    t = r['id']
    s = False
    ls = ""
    while not s:
        c = "/api/v1/vmware/vm/request"
        u = ("{}{}/{}".format(random.choice(node_ips), c, t))
        r = requests.get(u, headers=header, verify=False, timeout=15).json()
        ls = r['status']
        if ls == "SUCCEEDED":
            logging.info("{} - EXPORT SUCCEED - {} - {} - {} - {} - {}".format(
                v, r['nodeId'], h, r['startTime'], r['endTime']))
            if r['nodeId'] not in rn:
                rn[r['nodeId']] = 1
            else:
                rn[r['nodeId']] += 1
            m['successful_recovery'] += 1
            s = True
        if "FAIL" in ls:
            logging.error(
                "{} - Export FAIL - {} ({}) - Start ({}) - End ({})".format(
                    v, r['nodeId'], r['startTime'], r['endTime']))
            logging.error(r['error'])
            m['failed_operations'] += 1
            s = True
        time.sleep(5)
    return


# Returns latest snap_id from vm_id - if config['recovery_point'] then find closest to time without going over
# 2019-09-15T07:02:54.470Z
def get_snapshot_id(vin):
    myrc = {}
    if 'recovery_point' in config:
        mrp = pytz.utc.localize(parse(config['recovery_point']))
    else:
        mrp = pytz.utc.localize(datetime.now())
    for v in vin:
        c = "/api/v1/vmware/vm/"
        u = ("{}{}{}".format(random.choice(node_ips), c, urllib.parse.quote(v)))
        r = requests.get(u, headers=header, verify=False, timeout=15).json()
        if r['snapshotCount'] > 0:
            for snap in r['snapshots']:
                dt = parse(snap['date'])
                if mrp > dt:
                    diff = abs(mrp - dt)
                    myrc[diff] = {}
                    myrc[diff]['id'] = snap['id']
                    myrc[diff]['dt'] = snap['date']
                    myrc[diff]['vmid'] = v
    close = min(myrc)
    logging.info(
        "{} - RP SUCCEED - Snap {} - RP {})".format(r['name'], myrc[close]['dt'], mrp))
    return myrc[close]['id'], myrc[close]['vmid']


def print_m(m):
    print("\n Job Statistics:")
    for i in m:
        if m[i] != 0:
            print("\t {} : {}".format(i.replace('_', ' ').title(), m[i]))
            logging.info("{} : {}".format(i.replace('_', ' ').title(), m[i]))

    for i in ['kpi_function', 'kpi_svm']:
        if eval(i):
            kpi = eval(i)
            c = {'median': round(statistics.median_high(kpi), 3),
                 'mean': round(statistics.mean(kpi), 3),
                 'min': round(min(kpi), 3),
                 'max': round(max(kpi), 3)}
            print("Per Operation Stats for {}:".format(i.replace('kpi_', '').title()))
            logging.info("Per Operation Stats for {}:".format(i.replace('kpi_', '').title()))
            for o in c:
                print("\t {} : {}".format(o.title(), c[o]))
                logging.info("{} : {}".format(o.title(), c[o]))


if __name__ == '__main__':
    # Get Rubrik Nodes so we can thread against them
    print("Getting Rubrik Node Information", end='')
    node_ips = get_ips(config['rubrik_host'])
    print(" - Done")

    # Get VMware structure so that we can round robin
    if config['function'] == 'export' or config['svm']:
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

    # start the svm processor
    if config['svm']:
        svm_vm = Queue()
        svm_threads = []
        for i in range(config['svm_threads']):
            svm_process = Thread(target=relocate_vm, args=(svm_vm,))
            svm_threads.append(svm_process)
        #    svm_process.setDaemon(True)
            svm_process.start()

    # Run the recoveries
    print("Running Recovery")
    run_threads(data, config['function_threads'], run_function)
    end = timer()
    progress(len(data), len(data), "Completed in {} seconds                                              ".format(round(end - start, 3)))
    m['time_elapsed'] = round(end - start, 3)
    m['start_time'] = startTime
    endTime = datetime.now()
    m['end_time'] = endTime
    print('')

    if config['svm']:
        while not svm_vm.empty():
            main_thread = threading.current_thread()
            s = "Storage vMotion: ({} Complete,  {} Running,  {} Queued)".format(m['successful_relocate'], m['active_svm'], svm_vm.qsize())
            sys.stdout.write(s + "\r")
            sys.stdout.flush()
            time.sleep(1)

        for s in svm_threads:
            s.join()

        if svm_vm.empty():
            s = "Storage vMotion: ({} Complete,  {} Running,  {} Queued)".format(m['successful_relocate'], m['active_svm'], svm_vm.qsize())
            sys.stdout.write(s + "\n")
            print("Relocation Complete")

    print_m(m)

    for i in rn:
        logging.info("Recoveries Serviced {} - {}".format(i, rn[i]))

    for h in recoveries:
        logging.info("Recoveries Serviced {} - {}".format(h, recoveries[h]))

exit()
