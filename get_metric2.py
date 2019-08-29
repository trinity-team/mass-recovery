from pyVim import connect
from pyVmomi import vim
import pprint

pp = pprint.PrettyPrinter(indent=4)
import datetime
import tools.cli as cli
import ssl
import sys
import warnings

warnings.filterwarnings("ignore")

ssl._create_default_https_context = ssl._create_unverified_context

host_name = "poc-esx01.rangers.lab"
args = cli.get_args()
service_instance = connect.SmartConnect(host=args.host,
                                        user=args.user,
                                        pwd=args.password,
                                        port=int(args.port))


def find_hostsystem_by_name(content, hostname):
    host_system = get_all_objs(content, [vim.HostSystem])
    for host in host_system:
        if host.name == hostname:
            return host
    return None


def get_all_objs(content, vimtype, folder=None, recurse=True):
    if not folder:
        folder = content.rootFolder
    obj = {}
    container = content.viewManager.CreateContainerView(folder, vimtype, recurse)
    for managed_object_ref in container.view:
        obj.update({managed_object_ref: managed_object_ref.name})
    return obj


startTime = datetime.datetime.now() - datetime.timedelta(minutes=20)
content = service_instance.RetrieveContent()
perfManager = content.perfManager
host_mo = find_hostsystem_by_name(content, host_name)
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
        calc = round(calc/samp)
        if val.id.instance == '':
            print("STAT - {} - {} - {}{} ({} points)".format(host_mo.name, co, calc, un, samp))
        else:
            print("STAT - {} - {} ({}) - {}{} ({} points)".format(host_mo.name, co, val.id.instance, calc, un, samp))
