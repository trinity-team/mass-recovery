import requests, sys, time, random, csv, urllib.parse, logging, datetime, json, os, statistics
from timeit import default_timer as timer
from multiprocessing.pool import ThreadPool
from requests.packages.urllib3.exceptions import InsecureRequestWarning

config = json.load(open(sys.argv[1]))
if 'debug' not in config:
    config['debug'] = False

if 'max_hosts' not in config:
    config['max_hosts'] = 0

sla = "Bronze"
rn = {}
timestr = time.strftime("%Y%m%d-%H%M%S")
d = "{}_{}_{}".format(config['threads'], config['max_hosts'], config['limit'])

kpi = []

vmw_file = 'cache/{}.vmw'.format(config['rubrik_host'])
ds_file = 'cache/{}.ds'.format(config['rubrik_host'])

os.makedirs('log', exist_ok=True)
logging.basicConfig(
    filename='log/mass_{}_{}_{}.log'.format(config['function'], timestr, d),
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

track = {}

m = {"snap_not_found": 0,
     "vm_not_found": 0,
     "can_be_recovered": 0,
     "successful_recovery": 0,
     "successful_livemount": 0,
     "successful_unmount": 0,
     "failed_operations": 0,
     "max_hosts": config['max_hosts'],
     "thread_count": config['threads']
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
    b = timer()
    vi, hs = get_vm_id(vm['Object Name'])
    if m['can_be_recovered'] == config['limit']:
        return
    if vi is None:
        logging.warning("{} - VM Not Found on Rubrik".format(vm['Object Name']))
        m['vm_not_found'] += 1
        return
    si = get_snapshot_id(vi)
    if si is None:
        logging.warning("{} - Snapshot not found for VM".format(vm['Object Name']))
        m['snap_not_found'] += 1
        return
    m['can_be_recovered'] += 1
    if config['function'] == 'livemount':
        livemount_vm(vm['Object Name'], si)
    elif config['function'] == 'unmount':
        unmount_vm(vm['Object Name'], vi)
    elif config['function'] == 'export':
        # Select next hosts if not using max_hosts
        if ('ESX Cluster' not in vm) or (vm['ESX Cluster'] == '') or (vm['ESX Cluster'] is None):
            vm['ESX Cluster'] = hs
        if len(recoveries) <= (config['max_hosts'] - 1):
            # h = (list(vm_struc[vm['ESX Cluster']]['hosts']))[len(recoveries)]
            h = random.choice(list(vm_struc[vm['ESX Cluster']]['hosts']))
        # Select host from used host that has least executions
        else:
            h = min(recoveries, key=recoveries.get)
        # See if I'm assigning a new datastore in the csv, or just use the last known
        if ('Datastore' not in vm) or (vm['Datastore'] == '') or (vm['Datastore'] is None):
            vm['Datastore'] = datastore_map[get_vdisk_id(vi)]
        # Add host to used host array
        if h not in recoveries:
            recoveries[h] = 1
        else:
            recoveries[h] += 1
        di = (vm_struc[vm['ESX Cluster']]['hosts'][h]['datastores'][vm['Datastore']]['id'])
        logging.info("{} - Export {} to {} (disk {})".format(vm['Object Name'], si, h, di))
        hi = (vm_struc[vm['ESX Cluster']]['hosts'][h]['id'])
        export_vm(vm['Object Name'], si, hi, di, h)
        f = timer()
        kpi.append(f-b)
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
    os.makedirs('cache', exist_ok=True)
    try:
        with open(vmw_file) as j:
            h = json.load(j)
    except FileNotFoundError:
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
                if response_details['name'] in config['omit_hosts']:
                    continue
                if hc == config['max_hosts']:
                    continue
                hc += 1
                h[response['name']]['hosts'][response_details['name']] = {'id': response_details['id']}
                h[response['name']]['hosts'][response_details['name']]['datastores'] = {}
                call = "/api/v1/vmware/host"
                uri = ("{}{}/{}".format(random.choice(node_ips), call, response_details['id']))
                request = requests.get(uri, headers=header, verify=False, timeout=15).json()
                for response_datastores in request['datastores']:
                    h[response['name']]['hosts'][response_details['name']]['datastores'][
                        response_datastores['name']] = {
                        'id': response_datastores['id']}
        with open(vmw_file, 'w') as o:
            json.dump(h, o)
    return h


# Set SLA
def set_vm_sla(v):
    c = "/api/v1/vmware/vm"
    lo = {
        "configuredSlaDomainId": "{}".format(get_sla_id(sla))
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
        r = requests.get(u, headers=header, verify=False, timeout=15).json()
        for z in r['data']:
            cc = "/api/internal/vmware/datastore/"
            uu = ("{}{}{}".format(random.choice(node_ips), cc, z['id']))
            rr = requests.get(uu, headers=header, verify=False, timeout=30).json()
            if 'virtualDisks' in rr:
                for vd in rr['virtualDisks']:
                    dsm[vd['id']] = z['name']
        with open(ds_file, 'w') as o:
            json.dump(dsm, o)
    return dsm


# Returns vm_id from vm_name
def get_vm_id(v):
    c = "/api/v1/vmware/vm"
    u = ("{}{}?name={}".format(random.choice(node_ips), c, urllib.parse.quote(v)))
    r = requests.get(u, headers=header, verify=False, timeout=15).json()
    for response in r['data']:
        if response['name'] == v:
            return response['id'], response['infraPath'][-2]['name']


def livemount_table():
    lma = {}
    c = "/api/v1/vmware/vm/snapshot/mount"
    u = ("{}{}?limit=9999".format(random.choice(node_ips), c))
    r = requests.get(u, headers=header, verify=False, timeout=15).json()
    for response in r['data']:
        if response['vmId'] not in lma:
            lma[response['vmId']] = []
        lma[response['vmId']].append(response['id'])
    return lma


def unmount_vm(v, vi):
    c = "/api/v1/vmware/vm/snapshot/mount/"
    if vi in lmt:
        for si in lmt[vi]:
            u = ("{}{}{}".format(random.choice(node_ips), c, si))
            logging.info("{} - {} - {} - {}".format(v, 'Unmounting', vi, si))
            m['successful_unmount'] += 1
            r = requests.delete(u, headers=header, verify=False, timeout=15).json()
    return


def livemount_vm(v, si):
    c = "/api/v1/vmware/vm/snapshot"
    lo = {
        "disableNetwork": True,
        "removeNetworkDevices": False,
        "powerOn": False,
    }
    u = ("{}{}/{}/mount".format(random.choice(node_ips), c, si))
    r = requests.post(u, json=lo, headers=header, verify=False, timeout=15).json()
    t = r['id']
    s = False
    ls = ""
    while not s:
        c = "/api/v1/vmware/vm/request"
        u = ("{}{}/{}".format(random.choice(node_ips), c, t))
        r = requests.get(u, headers=header, verify=False, timeout=15).json()
        ls = r['status']
        if ls == "SUCCEEDED":
            logging.info(
                "{} - {} - {} - {} - {} ".format(v, r['status'], r['nodeId'], r['startTime'], r['endTime']))
            m['successful_livemount'] += 1
            s = True
        if "FAIL" in ls:
            logging.error("{} - Livemount Status - {} ({}) - Start ({}) - End ({})".format(v, r['status'], r['nodeId'],
                                                                                           r['startTime'],
                                                                                           r['endTime']))
            m['failed_operations'] += 1
            s = True
        time.sleep(3)
    return


def export_vm(v, si, hi, di, h):
    c = "/api/v1/vmware/vm/snapshot"
    lo = {
        "vmName": "{}{}".format(config['prefix'], v),
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
            logging.error("{} - Export Status - {} ({}) - Start ({}) - End ({})".format(v, r['status'], r['nodeId'],
                                                                                        r['startTime'], r['endTime']))
            m['failed_operations'] += 1
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
        if m[i] != 0:
            print("\t {} : {}".format(i.replace('_', ' ').title(), m[i]))
            logging.info("{} : {}".format(i.replace('_', ' ').title(), m[i]))
    if kpi:
        median = round(statistics.median_high(kpi),3)
        mean = round(statistics.mean(kpi),3)
        mn = round(min(kpi),3)
        mx = round(max(kpi),3)
        print("Operation Stats:".format(i.replace('_', ' ').title(), m[i]))
        print("\t {} : {}".format('Median', median))
        logging.info("{} : {}".format('Median', median))
        print("\t {} : {}".format('Mean', mean))
        logging.info("{} : {}".format('Mean', mean))
        print("\t {} : {}".format('Min', mn))
        logging.info("{} : {}".format('Min', mn))
        print("\t {} : {}".format('Max', mx))
        logging.info("{} : {}".format('Max', mx))


def get_objs(c, t, f=None, r=True):
    if not f:
        f = c.rootFolder
    obj = {}
    container = c.viewManager.CreateContainerView(f, t, r)
    for managed_object_ref in container.view:
        obj.update({managed_object_ref: managed_object_ref.name})
    return obj


def find_host(c, n):
    hs = get_objs(c, [vim.HostSystem])
    for o in hs:
        if o.name == n:
            return o
    return None


# Get Rubrik Nodes so we can thread against them
print("Getting Rubrik Node Information", end='')
node_ips = get_ips(config['rubrik_host'])
print(" - Done")

# Get VMware structure so that we can round robin
if config['function'] == 'export':
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
if config['limit']:
    data = data[0:config['limit']]
print(" - Done")

# Run the recoveries
print("Running Recovery", end='')
run_assessment_threads(data, config['threads'])
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

for h in recoveries:
    logging.info("Recoveries Serviced {} - {}".format(h, recoveries[h]))

# This happy mess will grab all performance metrics from vCenter that are available for each ESX host that
# serviced requests. Currently it's just writing net.*
if config['debug']:
    from pyVim import connect
    from pyVmomi import vim

    for host_name in recoveries:
        # Log into the ESX Host
        service_instance = connect.SmartConnect(host=host_name,
                                                user=config['esx_user'],
                                                pwd=config['esx_pass']
                                                )
        content = service_instance.RetrieveContent()
        perfManager = content.perfManager
        host_mos = find_host(content, host_name)
        counters = {}
        # Assemble a hash of details for the counters
        for ct in perfManager.perfCounter:
            cfn = ct.groupInfo.key + "." + ct.nameInfo.key + "." + ct.rollupType
            counters[ct.key] = {}
            counters[ct.key]['name'] = cfn
            counters[ct.key]['unit'] = ct.unitInfo.label
        # Query for the counters
        counterIDs = [m.counterId for m in perfManager.QueryAvailablePerfMetric(entity=host_mos)]
        metricIDs = [vim.PerformanceManager.MetricId(counterId=c, instance="*") for c in counterIDs]
        spec = vim.PerformanceManager.QuerySpec(entity=host_mos,
                                                metricId=metricIDs,
                                                startTime=startTime)
        q = perfManager.QueryStats(querySpec=[spec])
        # Figure out what to log
        for val in q[0].value:
            if "net.bytes" in counters[val.id.counterId]['name'] or "net.usage" in counters[val.id.counterId]['name']:
                calc = 0
                samp = 0
                metric_max = 0
                if val.id.instance == '':
                    for v in val.value:
                        if v != -1:
                            calc += v
                            if v > metric_max:
                                metric_max = v
                            samp += 1
                    calc = round(calc / samp)
                    logging.info("{} - {} - avg:{}{} max:{}{} samples:{} - experimental".format(host_mos.name,
                                                                                                counters[
                                                                                                    val.id.counterId][
                                                                                                    'name'],
                                                                                                calc,
                                                                                                counters[
                                                                                                    val.id.counterId][
                                                                                                    'unit'],
                                                                                                metric_max,
                                                                                                counters[
                                                                                                    val.id.counterId][
                                                                                                    'unit'],
                                                                                                samp))
        connect.Disconnect(service_instance)
exit()

