#!/usr/bin/env python

import sys

from gratia.gip.ldap import read_bdii, config_file
from gratia.gip.common import join_FK

def create_count_dict(entries):
    """
    Convert a list of all the CE's LDAP entries to a dictionary which uses the 
    cluster name as the key and the estimated number of CPUs at the site as 
    the value.
    """
    cluster_info = {}
    for entry in entries:
        cpus = int(entry.glue['CEInfoTotalCPUs'])
        cluster = entry.glue['CEHostingCluster']
        if (cluster in cluster_info and cluster_info[cluster] <= cpus) or \
               (cluster not in cluster_info):
           cluster_info[cluster] = cpus
    return cluster_info

def sub_cluster_info(ce_list, cp):
    """
    Given a list of CE names (not LDAP entries), return a dictionary where
    the key is the CE name and the value is a list of SubClusters associated
    with that CE.
    """
    sc_entries = read_bdii(cp, query="(objectClass=GlueSubCluster)")
    sc_info = {}
    sc_total = {}
    for ce in ce_list:
        my_sc = sc_info.get(ce, [])
        sc_info[ce] = my_sc
        for sc in sc_entries:
            desired_ck = "GlueClusterUniqueID=%s" % ce
            if "ChunkKey" in sc.glue and sc.glue["ChunkKey"] == desired_ck:
                my_sc.append(sc)
    return sc_info

def correct_vo(vo, cp):
    """
    Helper function for the ownership_info.  Given a VO sponsor name, 
    normalize it to one of our recognized VOs.
    """
    vo = vo.lower()
    correct_vos = eval(cp.get("cpu_count", "correct_vos"))
    if vo in correct_vos:
        vo = correct_vos[vo]
    return vo

def ownership_info(ce_entries, cp):
    """
    Determine ownership of clusters from the sites's SiteSponsor attribute.
    """
    # Query BDII for the cluster and site entries
    cluster_entries = read_bdii(cp, query="(objectClass=GlueCluster)")
    site_entries = read_bdii(cp, query="(objectClass=GlueSite)")
    ownership = {}

    # Determine the site's advertised ownership.
    for ce in ce_entries:
        # First, we join the CE to the cluster:
        cluster = join_FK(ce, cluster_entries, "ClusterUniqueID")
        # Then, join the cluster to the site:
        site = join_FK(cluster, site_entries, "SiteUniqueID")
        try:
            ownership[ce] = site.glue["SiteSponsor"]
            #print site.glue["SiteName"], site.glue["SiteSponsor"]
        except:
            ownership[ce] = "unknown"
                    
    # Refine ownership; turn string into list of tuples and make sure
    # that everything adds up to 100%.
    # This is a bit awkward.  I should consider turning list of tuples
    # into a dictionary.
    refined_ownership = {}
    for ce, val in ownership.items():
        val = val.lower()
        refined = []
        ctr = 0
        for entry in val.split():
            info = entry.split(':')
            vo = correct_vo(info[0], cp)
            if len(info) == 1:
                refined.append((vo, 100))
                ctr += 100
            else:
                try:
                    refined.append((vo, int(info[1])))
                    ctr += int(info[1])
                except:
                    print entry
                    raise
        if ctr < 100:
            new_refined = []
            has_unknown = False
            for entry in refined:
                if entry[0] == "unknown":
                    new_refined.append(("unknown", entry[1]+(100-ctr)))
                    has_unknown = True
                else:
                    new_refined.append(entry)
            if not has_unknown:
                new_refined.append(("unknown", 100-ctr))
            refined = new_refined
        refined_ownership[ce.glue["CEInfoHostName"]] = refined
    return refined_ownership

def correct_count(core_info, ksi2k_info, ownership, correction, duplicate):
    """
    Perform the corrections for the aggregate totals.  This applies duplicate
    rules as well as correction rules.

    Each correction rule is of the form:
        ce = <python expression>
    where the variables of the python expression are the core count of the
    other CEs in the OSG.  We convert hostnames into python-variables by 
    replacing "dangerous" characters to underscores:
        host-1.unl.edu -> host_1_unl_edu

    For example, the FERMIGRID entry includes results from other clusters so
    we do the following:
        "fermigrid1.fnal.gov" : "fermigrid1_fnal_gov-fngp_osg_fnal_gov-cmsosgce3_fnal_gov"
    """
    core_count = 0
    msi2k_count = 0
    core_locals = {}
    ksi2k_locals = {}
    vo_info = {}
    # Build the locals dictionary
    for cluster in core_info:
        safe_cluster = cluster.replace('.', '_').replace('-', '_')
        core_locals[safe_cluster] = core_info[cluster]
        ksi2k_locals[safe_cluster] = ksi2k_info[cluster]

    for cluster in core_info:
        if cluster in duplicate:
            is_duplicate = False
            for entry in duplicate[cluster]:
                if entry in core_info:
                    print "Not counting %s because it is a duplicate." % \
                        cluster
                    is_duplicate = True
                    break
            if is_duplicate:
                continue
        cores = core_info[cluster]
        ksi2k = ksi2k_info[cluster]
        if cluster in correction:
            old_cores = cores
            old_ksi2k = ksi2k
            cores = eval(correction[cluster], core_locals)
            ksi2k = eval(correction[cluster], ksi2k_locals)
            print "Correction factor for %s; before %i cores, %i KSI2K; after" \
                " %i cores, %i KSI2K" % (cluster, old_cores, old_ksi2k, \
                cores, ksi2k)
        core_count += cores
        msi2k_count += ksi2k/1000.0
        for info in ownership[cluster]:
            vo, amt = info
            old_info = vo_info.get(vo, [0, 0])
            old_info[0] += cores * (amt / 100.0)
            old_info[1] += ksi2k * (amt / 100.0) / 1000.0
            vo_info[vo] = old_info
    return core_count, msi2k_count, vo_info

def pretty_ownership(entry):
    """
    Helper function to make the ownership entry into a nicely-formatted string.
    """
    output = ''
    for info in entry:
        output += "%s: %i%%, " % info
    return output[:-2]

def correct_sc_info(cluster, cpu, sc_info, specint):
    """
    Correct the information in the subclusters and set the
    KSI2K value for the subcluster.
    """
    for sc in sc_info[cluster]:
        phy_cpus = int(sc.glue["SubClusterPhysicalCPUs"])
        log_cpus = int(sc.glue["SubClusterLogicalCPUs"])
        # If the physical CPUs were set by the admin instead of the
        # logical CPUs, then transfer that setting over.
        if phy_cpus > 4 and log_cpus in [0, 2, 4, 8]:
            sc.glue["SubClusterLogicalCPUs"] = phy_cpus
            log_cpus = phy_cpus
        # If the subcluster information looks suspiciously like
        # information for only one host, set it to the CPUs in
        # the cluster.  This is only active when there is one
        # subcluster (as sites like UCSD purposely put in even
        # very small sub clusters).
        if log_cpus in [2, 4, 8] and len(sc_info[cluster]) == 1:
            sc.glue["SubClusterLogicalCPUs"] = cpu
        # The benchmark values are hardcoded to 400.  If the hardcoded
        # value has not been changed, then pull it from the lookup table
        # in the config file.
        if int(sc.glue["HostBenchmarkSI00"]) == 400:
            cpu_model = sc.glue["HostProcessorModel"]
            if cpu_model not in specint:
                raise KeyError("Unknown CPU model: %s" % cpu_model)
            sc.glue["HostBenchmarkSI00"] = specint[cpu_model]
        # Finally, the KSI2K value is the per-core number multiplied by
        # the number of cores.
        ksi2k = int(sc.glue["HostBenchmarkSI00"])* \
            int(sc.glue["SubClusterLogicalCPUs"]) / 1000
        sc.glue["KSI2K"] = ksi2k


def main():
    # Determine any filters we should apply
    if len(sys.argv) > 1:
        ce_glob = sys.argv[1]
    else:
        ce_glob = "*"

    # Load up the config file.
    cp = config_file()

    # Read the CE entries from the BDII.    
    entries = read_bdii(cp, 
        query="(&(objectClass=GlueCE)(GlueCEInfoHostName=%s))" % ce_glob)
    cluster_info = create_count_dict(entries)
    sc_info = sub_cluster_info(cluster_info.keys(), cp)
    specint = eval(cp.get("cpu_count", "specint2k"))
    correction = eval(cp.get("cpu_count", "correction"))
    duplicate = eval(cp.get("cpu_count", "duplicate"))
    msi2k_ctr = 0.0
    ksi2k_info = {}
    ownership = ownership_info(entries, cp)
    gk_ctr = 0
    for cluster, cpu in cluster_info.items():
        print "* Cluster: ", cluster
        my_sc_cores = 0
        ksi2k_ctr = 0
        correct_sc_info(cluster, cpu, sc_info, specint)
        
        # Print out SC info.
        if len(sc_info[cluster]) > 0:
            print " - Sub-clusters:"
        for sc in sc_info[cluster]:
            ksi2k = sc.glue["KSI2K"]
            msi2k_ctr += ksi2k / 1000.0
            my_sc_cores += int(sc.glue["SubClusterLogicalCPUs"])
            print "   - %(SubClusterUniqueID)s, CPU Model:" \
                " %(HostProcessorModel)s, Cores: %(SubClusterLogicalCPUs)s," \
                " KSI2K: %(KSI2K)s" % sc.glue
            ksi2k_ctr += ksi2k
        
        # Do any KSI2K/CPU adjustments necessary.
        if my_sc_cores == 0:
            avg_ksi2k = 1.3
        else:
            avg_ksi2k = ksi2k_ctr / float(my_sc_cores)
        if my_sc_cores > cpu: # Not enough CPUs; use sum from SC.
            cpu = my_sc_cores
            cluster_info[cluster] = cpu
        elif my_sc_cores < cpu: # Not enough KSI2K; add average froom SCs.
            addl_ksi2k = avg_ksi2k * (cpu - my_sc_cores)
            print " - Additional kSI2K for %s: %i" % (cluster, addl_ksi2k)
            ksi2k_ctr += addl_ksi2k
            msi2k_ctr += addl_ksi2k / 1000.0
        ksi2k_info[cluster] = ksi2k_ctr

        # Print out any correction factors or duplicate clusters
        if cluster in correction:
            print " - Correction factor: %s" % correction[cluster]
        if cluster in duplicate:
            print " - Duplicates of this cluster: %s" % duplicate[cluster]
        print " - Ownership:", pretty_ownership(ownership[cluster])
        print " - Core count:", cpu
        print " - KSI2K: %.1f" % ksi2k_ctr
        gk_ctr += 1

    print "----------------------------"
    core_count, msi2k_count, vo_info = correct_count(cluster_info, ksi2k_info, 
        ownership, correction, duplicate)
    print "----------------------------"
    print "OSG cores sum:", core_count
    print "OSG MSI2K: %.2f" % msi2k_count
    print "OSG gatekeepers count:", gk_ctr
    print "----------------------------"
    other_cores = 0
    other_msi2k = 0
    other_vos = []
    print_vos = [i.strip() for i in cp.get("cpu_count", "print_vos").split(',')]
    for vo, info in vo_info.items():
        if vo not in print_vos:
            other_cores += info[0]
            other_msi2k += info[1]
            other_vos.append(vo)
            continue
        print "%s cores sum: %i" % (vo, info[0])
        print "%s MSI2K: %.2f" % (vo, info[1])

    print "Other cores sum: %i" % other_cores
    print "Other MSI2K: %.2f" % other_msi2k
    print "Other VOs:", other_vos

if __name__ == '__main__':
    main()

