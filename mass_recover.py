import requests, sys, time, random, csv, urllib.parse, logging, datetime, pprint, json
from timeit import default_timer as timer
from multiprocessing.pool import ThreadPool
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from pyVim import connect
from pyVmomi import vim

pp = pprint.PrettyPrinter(indent=4)

config = json.load(open('config.json'))

threads = 5
max_hosts = 3
limit = 50
in_file = 'in_data_full.csv'
export = True
debug = True

# DO NOT MODIFY BELOW
sla = "Bronze"
hu = []
rn = {}
timestr = time.strftime("%Y%m%d-%H%M%S")
d = "{}_{}".format(threads, limit)
logging.basicConfig(
    filename='mass_recover_{}_{}.log'.format(timestr, d),
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

m = {"snap_not_found": 0,
     "vm_not_found": 0,
     "can_be_recovered": 0,
     "successful_recovery": 0,
     "failed_recovery": 0,
     "max_hosts": max_hosts,
     "thread_count": 0
     }

recoveries = {}

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
start = timer()
startTime = datetime.datetime.now()

# Use Token Auth Headers
auth_header = 'Bearer ' + config['rubrik_key']
header = {'Accept': 'application/json', 'Authorization': auth_header}


# Progress Bar
def progress(c, t, s=''):
    bl = 60
    fl = int(round(bl * c / float(t)))
    p = round(100.0 * c / float(t), 1)
    b = '=' * fl + '-' * (bl - fl)
    sys.stdout.write('[%s] %s%s (%s)\r' % (b, p, '%', s))
    sys.stdout.flush()
    if c == t:
        sys.stdout.flush()


# Threader
def run_assessment_threads(v, t):
    m['thread_count'] = t
    p = ThreadPool(t)
    t = len(v)
    r = p.map_async(run_assessment_process, v, chunksize=1)
    while not r.ready():
        progress((t - r._number_left), t, "{} of {}".format(t - r._number_left, t))
    p.close()
    p.join()
    return r.get()


# Worker Process
def run_assessment_process(vm):
    vi = get_vm_id(vm['Object Name'])
    if vi is None:
        logging.warning("{} - VM Not Found on Rubrik".format(vm['Object Name']))
        m['vm_not_found'] += 1
        return
    si = get_snapshot_id(vi)
    if si is None:
        logging.warning("{} - Snapshot not found for VM".format(vm['Object Name']))
        m['snap_not_found'] += 1
        return
    h = random.choice(list(vm_struc[vm['ESX Cluster']]['hosts']))
    if h not in hu:
        hu.append(h)
    if h not in recoveries:
        recoveries[h] = 1
    else:
        recoveries[h] += 1
    logging.info("{} - Export {} to {}".format(vm['Object Name'], si, h))
    m['can_be_recovered'] += 1
    hi = (vm_struc[vm['ESX Cluster']]['hosts'][h]['id'])
    di = (vm_struc[vm['ESX Cluster']]['hosts'][h]['datastores'][vm['Datastore']]['id'])
    if export:
        export_vm(vm['Object Name'], si, hi, di, h)
    return m


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
    h = {}
    call = "/api/v1/vmware/compute_cluster"
    uri = ("{}{}?limit=999&primary_cluster_id=local".format(random.choice(node_ips), call))
    request = requests.get(uri, headers=header, verify=False, timeout=30).json()
    for response in request['data']:
        h[response['name']] = {'id': response['id']}
        call = "/api/v1/vmware/compute_cluster"
        uri = ("{}{}/{}".format(random.choice(node_ips), call, response['id']))
        request = requests.get(uri, headers=header, verify=False, timeout=60).json()
        h[response['name']]['hosts'] = {}
        hc = 0
        for response_details in request['hosts']:
            if hc == max_hosts:
                continue
            hc += 1
            h[response['name']]['hosts'][response_details['name']] = {'id': response_details['id']}
            h[response['name']]['hosts'][response_details['name']]['datastores'] = {}
            call = "/api/v1/vmware/host"
            uri = ("{}{}/{}".format(random.choice(node_ips), call, response_details['id']))
            request = requests.get(uri, headers=header, verify=False, timeout=15).json()
            for response_datastores in request['datastores']:
                h[response['name']]['hosts'][response_details['name']]['datastores'][response_datastores['name']] = {
                    'id': response_datastores['id']}
    return h


# Set SLA
def set_vm_sla(v):
    c = "/api/v1/vmware/vm"
    lo = {
        "configuredSSlaDomainId": "{}".format(get_sla_id(sla))
    }
    u = ("{}{}/{}".format(random.choice(node_ips), c, v))
    r = requests.patch(u, json=lo, headers=header, verify=False, timeout=15).json()


def get_sla_id(s):
    c = "/api/v2/sla_domain"
    u = ("{}{}?name={}&primary_cluster_id=local".format(random.choice(node_ips), c, urllib.parse.quote(s)))
    r = requests.get(u, headers=header, verify=False, timeout=15).json()
    for o in r['data']:
        if o['name'] == sla:
            return o['id']


# Returns vm_id from vm_name
def get_vm_id(v):
    c = "/api/v1/vmware/vm"
    u = ("{}{}?name={}".format(random.choice(node_ips), c, urllib.parse.quote(v)))
    r = requests.get(u, headers=header, verify=False, timeout=15).json()
    for response in r['data']:
        if response['name'] == v:
            set_vm_sla(response['id'])
            return response['id']


def export_vm(v, si, hi, di, h):
    c = "/api/v1/vmware/vm/snapshot"
    lo = {
        "vmName": "EXP_{}".format(v),
        "disableNetwork": True,
        "removeNetworkDevices": False,
        "powerOn": False,
        "keepMacAddresses": False,
        "hostId": "{}".format(hi),
        "datastoreId": "{}".format(di),
        "unregisterVm": False,
        "shouldRecoverTags": True
    }
    u = ("{}{}/{}/export".format(random.choice(node_ips), c, si))
    r = requests.post(u, json=lo, headers=header, verify=False, timeout=15).json()
    t = r['id']
    s = False
    ls = ""
    while not s:
        c = "/api/v1/vmware/vm/request"
        u = ("{}{}/{}".format(random.choice(node_ips), c, t))
        r = requests.get(u, headers=header, verify=False, timeout=15).json()
        if ls != r['status']:
            logging.info("{} - Export Status - {}".format(v, r['status']))
        ls = r['status']
        if ls == "SUCCEEDED":
            logging.info(
                "{} - {} - {} - {} - {} - {}".format(v, r['status'], r['nodeId'], h, r['startTime'], r['endTime']))
            if r['nodeId'] not in rn:
                rn[r['nodeId']] = 1
            else:
                rn[r['nodeId']] += 1
            m['successful_recovery'] += 1
            s = True
        if "FAIL" in ls:
            logging.info("{} - Export Status - {} ({}) - Start ({}) - End ({})".format(v, r['status'], r['nodeId'],
                                                                                       r['startTime'], r['endTime']))
            m['failed_recovery'] += 1
            s = True
        time.sleep(3)
    return


# Returns latest snap_id from vm_id
def get_snapshot_id(i):
    c = "/api/v1/vmware/vm/"
    u = ("{}{}{}".format(random.choice(node_ips), c, urllib.parse.quote(i)))
    r = requests.get(u, headers=header, verify=False, timeout=15).json()
    if r['snapshotCount'] > 0:
        return r['snapshots'][0]['id']
    else:
        return


def print_m(m):
    for i in m:
        print("\t {} : {}".format(i.replace('_', ' ').title(), m[i]))
        logging.info("{} : {}".format(i.replace('_', ' ').title(), m[i]))


def get_objs(content, vimtype, folder=None, recurse=True):
    if not folder:
        folder = content.rootFolder
    obj = {}
    container = content.viewManager.CreateContainerView(folder, vimtype, recurse)
    for managed_object_ref in container.view:
        obj.update({managed_object_ref: managed_object_ref.name})
    return obj


# Get Rubrik Nodes so we can thread against them
print("Getting Rubrik Node Information", end='')
node_ips = get_ips(config['rubrik_host'])
print(" - Done")

# Get VMware structure so that we can round robin
print("Getting VMware Structures", end='')
vm_struc = get_vm_structure()
print(" - Done")

# Grab recovery info from csv
print("Getting Recovery Data", end='')
data = get_csv_data(in_file)
if limit:
    data = data[0:limit]
print(" - Done")

# Run the recoveries
print("Running Recovery", end='')
run_assessment_threads(data, threads)
print("Recovery Complete")
end = timer()
progress(len(data), len(data), "Completed in {} seconds".format(end - start))
m['time_elapsed'] = round(end - start, 3)
m['start_time'] = startTime
endTime = datetime.datetime.now()
m['end_time'] = endTime

print_m(m)
for i in rn:
    logging.info("Recoveries Serviced {} - {}".format(i, rn[i]))

for h in hu:
    logging.info("Recoveries Serviced {} - {}".format(h, recoveries[h]))

# This happy mess will grab all performance metrics from vCenter that are available for each ESX host that
# serviced requests. Currently it's just writing net.*
if debug:
    for host_name in hu:
        service_instance = connect.SmartConnect(host=host_name,
                                                user=config['esx_user'],
                                                pwd=config['esx_pass']
                                                )
        content = service_instance.RetrieveContent()
        perfManager = content.perfManager
        host_mo = get_objs(content, [vim.HostSystem])[0]
        counters = {}
        for ct in perfManager.perfCounter:
            cfn = ct.groupInfo.key + "." + ct.nameInfo.key + "." + ct.rollupType
            counters[ct.key] = {}
            counters[ct.key]['name'] = cfn
            counters[ct.key]['unit'] = ct.unitInfo.label
        counterIDs = [m.counterId for m in perfManager.QueryAvailablePerfMetric(entity=host_mo)]
        metricIDs = [vim.PerformanceManager.MetricId(counterId=c, instance="*") for c in counterIDs]
        spec = vim.PerformanceManager.QuerySpec(entity=host_mo,
                                                metricId=metricIDs,
                                                startTime=startTime)
        q = perfManager.QueryStats(querySpec=[spec])
        for val in q[0].value:
            co = counters[val.id.counterId]['name']
            un = counters[val.id.counterId]['unit']
            if "net.bytes" in co or "net.usage" in co:
                calc = 0
                samp = 0
                for v in val.value:
                    if v != -1:
                        calc += v
                        samp += 1
                calc = round(calc / samp)
                if val.id.instance == '':
                    print("STAT - {} - {} - {}{} ({} points)".format(host_mo.name, co, calc, un, samp))
                #else:
                #    print("STAT - {} - {} ({}) - {}{} ({} points)".format(host_mo.name, co, val.id.instance, calc, un, samp))
        connect.Disconnect(service_instance)
exit()
