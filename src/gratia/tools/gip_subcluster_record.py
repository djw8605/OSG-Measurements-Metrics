#!/usr/bin/env python

import os
import sys
import time
import types
import datetime

from gratia.gip.ldap import read_bdii, config_file
from gratia.gip.analysis import *
from gratia.gip.cpu_normalizations import get_cpu_normalizations
from graphtool.base.xml_config import XmlConfig

# Bootstrap our python configuration.  This should allow us to discover the
# configurations in the case where our environment wasn't really configured
# correctly.
paths = ['/opt/vdt/gratia/probe/common', '/opt/vdt/gratia/probe/services',
    '$VDT_LOCATION/gratia/probe/common', '$VDT_LOCATION/gratia/probe/services']
for path in paths:
    gratia_path = os.path.expandvars(path)
    if gratia_path not in sys.path and os.path.exists(gratia_path):
        sys.path.append(gratia_path)

import Gratia
import Subcluster

def main():

    # Load up the config file.
    cp = config_file()

    # Load the DB
    filename = os.path.expandvars("$HOME/dbinfo/DBParam.xml")
    if not os.path.exists(filename):
        filename = os.path.expandvars("$DBPARAM_LOCATION")
        if not os.path.exists(filename):
            filename = '/etc/DBParam.xml'
    x = XmlConfig(file=filename)
    conn = x.globals['GIPConnMan'].get_connection(None).get_connection()
    curs = conn.cursor()

    # Read the CE entries from the BDII.    
    entries = read_bdii(cp, query="(&(objectClass=GlueCE))")
        
    cluster_info = create_count_dict(entries)
    sc_info = sub_cluster_info(cluster_info.keys(), cp)
    specint = get_cpu_normalizations()

    now = datetime.datetime.now()

    curs.execute("DELETE FROM cpu_score");
    for cpu, score in specint.items():
        if isinstance(score, types.TupleType):
            score = score[0]
            #specint[cpu] = score
        curs.execute("INSERT INTO cpu_score VALUES (%s, %s, %s)", (cpu, \
            int(score), int(0)));

    site_ownership = create_site_dict(entries, cp)
    ownership = ownership_info(entries, cp)

    # Initialize the Probe's configuration
    ProbeConfig = '/etc/osg-storage-report/ProbeConfig'
    try:        
        Gratia.Initialize(ProbeConfig)
    except Exception, e:
        print e
        raise

    gratia_info = {}

    for cluster, cpu in cluster_info.items():
        print "* Cluster: ", cluster
        correct_sc_info(cluster, cpu, sc_info, specint)
        # Print out SC info.
        if len(sc_info[cluster]) > 0:
            print " - Sub-clusters:"
        for sc in sc_info[cluster]:
            print "   - %(SubClusterUniqueID)s, CPU Model:" \
                " %(HostProcessorModel)s, Cores: %(SubClusterLogicalCPUs)s," \
                " KSI2K: %(KSI2K)s" % sc.glue
            if int(sc.glue["HostBenchmarkSI00"]) != 400:
                cpu_si2k = int(sc.glue["HostBenchmarkSI00"])
            if cluster not in site_ownership:
                print >> sys.stderr, "Problem with %s site ownership; " \
                    "skipping." % cluster
                continue
            site = site_ownership[cluster]
            own = ownership[cluster]
            own_str = ''
            for entry in own:
                own_str += '%s:%s%%,' % entry
            curs.execute("INSERT INTO subcluster_score VALUES (%s, %s, %s, " \
                "%s, %s, %s, %s, %s)", (now, site, cluster, \
                sc.glue["SubClusterUniqueID"],
                sc.glue["SubClusterLogicalCPUs"], cpu_si2k, own_str, \
                sc.glue["HostProcessorModel"]))
            print >> sys.stderr, "Successfully inserted subcluster for site" \
                " %s" % site

            # Send the subcluster to Gratia
            Gratia.Config.setSiteName(site)
            Gratia.Config.setMeterName('gip_subcluster:%s' % cluster)

            s = Subcluster.Subcluster()
            s.UniqueID(sc.glue['SubClusterUniqueID'])
            s.Name(sc.glue['SubClusterName'])
            s.Cluster(cluster)
            #s.Platform()
            s.OS(sc.glue['HostOperatingSystemName'])
            s.OSVersion(sc.glue['HostOperatingSystemRelease'])
            s.Cores(sc.glue['SubClusterLogicalCPUs'])
            s.Cpus(sc.glue['SubClusterPhysicalCPUs'])
            s.RAM(sc.glue['HostMainMemoryRAMSize'])
            s.Processor(sc.glue['HostProcessorModel'])
            s.BenchmarkName('SI2K')
            s.BenchmarkValue(cpu_si2k)
            try:
                smp_size = int(sc.glue['HostArchitectureSMPSize'])
                cpus = int(sc.glue['SubClusterPhysicalCPUs'])
                s.Hosts(cpus/smp_size)
            except:
                pass
            s.Timestamp(time.time())
            site_list = gratia_info.setdefault((site, cluster), [])
            site_list.append(s)

    conn.commit()

    sendToGratia(gratia_info)

def sendToGratia(gratia_info):
    for cluster, subclusters in gratia_info.items():
        pid = os.fork()
        if pid == 0: # I am the child
            sendToGratia_child(cluster, subclusters)
            return
        else: # I am parent
            os.wait()

def sendToGratia_child(cluster, sc_list):
    site, cluster = cluster

    ProbeConfig = '/etc/osg-storage-report/ProbeConfig'
    try:
        Gratia.Initialize(ProbeConfig)
    except Exception, e:
        print e
        return
    Gratia.Config.setSiteName(site)
    Gratia.Config.setMeterName('gip_subcluster:%s' % cluster)

    for s in sc_list:
        print "Sending subcluster of cluster %s in site %s to Gratia: %s."% \
            (cluster, site, Gratia.Send(s))
        
if __name__ == '__main__':
    main()

