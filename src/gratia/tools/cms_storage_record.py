#!/usr/bin/env python

import os
import sys
import signal
import logging

logging.basicConfig(filename="/var/log/cms_storage_record.log")
log = logging.getLogger()

from gratia.gip.ldap import read_bdii
from gratia.gip.common import join_FK

paths = ['/opt/vdt/gratia/probe/common', '/opt/vdt/gratia/probe/services',
    '$VDT_LOCATION/gratia/probe/common', '$VDT_LOCATION/gratia/probe/services']
for path in paths:
    gratia_path = os.path.expandvars(path)
    if gratia_path not in sys.path and os.path.exists(gratia_path):
        sys.path.append(gratia_path)

import Gratia
import StorageElement
import StorageElementRecord

_se_to_site_cache = {}
def match_se_to_site(se, sites):
    global _se_to_site_cache
    if se in _se_to_site_cache:
        return _se_to_site_cache[se]
    try:
        site = join_FK(se, site_entries, "SiteUniqueID")
    except ValueError, ve:
        log.warn("Unable to match SE:\n%s" % entry)
        return None
    _se_to_site_cache[se] = site

def do_cms_se_info(cp):
    site_entries = read_bdii(cp, "(objectClass=GlueSite)")
    se_entries = read_bdii(cp, "(objectClass=GlueSE)")
    sa_entries = read_bdii(cp, "(objectClass=GlueSA)", multi=True)
    today = datetime.date.today()
    time_now = time.time()

    gratia_info = {}
    for sa in sa_entries:
        supports_cms = False
        for acbr in sa.glue['SAAccessControlBaseRule']:
            if 'cms' in acbr.lower():
                support_cms = True
                break
        if not supports_cms:
            continue
        try:
            total = int(sa.glue['SATotalOnlineSize'][0])
            free =  int(sa.glue['SAFreeOnlineSize'][0])
            used =  int(sa.glue['SAUsedOnlineSize'][0])
        except:
            log.warn("Unable to parse attributes:\n%s" % entry)
            continue

        try:
            se = join_FK(sa, se_entries, "SEUniqueID")
        except ValueError, ve:
            log.warn("Unable to match SA to SE:\n%s" % entry)
            continue
        site = match_se_to_site(se, site_entries)
        if not site:
            log.warn("Unable to match SE %s to site." % \
                entry.glue['SEUniqueID'])
            continue
        se_unique_id = se.glue['SEUniqueID']
        sa_name = sa.glue['SAName']
        probeName = 'gip_storage:%s' % se_unique_id
        se_name = se.glue['SEName']
        gse = StorageElement.StorageElement()
        space_unique_id = "%s:%s:%s" % (se_unique_id, "GlueStorageArea",
            sa_name)
        gse.ParentID("%s:%s:%s" % (se_unique_id, "SE", se_name))
        gse.UniqueID(space_unique_id)
        gse.SE(se_name)
        gse.Name(sa_name)
        gse.SpaceType("GlueStorageArea")
        gse.Timestamp(time_now)
        gse.Implementation(se.glue['SEImplementationName'])
        gse.Version(se.glue['SEImplementationVersion'])
        gse.Status(se.glue['SEStatus'])
        se_list = gratia_info.setdefault((probeName, se_name), [])
        se_list.append(se)

        ser = StorageElementRecord.StorageElementRecord()
        ser.UniqueID(space_unique_id)
        ser.MeasurementType("logical")
        ser.StorageType("disk")
        ser.Timestamp(time_now)
        ser.TotalSpace(total*1000**3)
        ser.FreeSpace(free*1000**3)
        ser.UsedSpace(used*1000**3)
        se_list.append(ser)

    sendToGratia(gratia_info)

def sendToGratia(gratia_info):
    for info, records in gratia_info.items():
        pid = os.fork()
        if pid == 0: # I am the child
            signal.alarm(5*60)
            try:
                sendToGratia_child(info, records)
            except Exception, e:
                log.exception(e)
                os._exit(0)
        else: # I am parent
            try:
                os.waitpid(pid)
            except:
                pass

def sendToGratia_child(info, record_list):
    probeName, site = info

    ProbeConfig = '/etc/osg-storage-report/ProbeConfig'
    try:
        Gratia.Initialize(ProbeConfig)
    except Exception, e:
        log.exception(e)
        return
    Gratia.Config.setSiteName(site)
    Gratia.Config.setMeterName(probeName)
    Gratia.Handshake()
    try:
        Gratia.SearchOutstandingRecord()
    except Exception, e:
        log.exception(e)
    Gratia.Reprocess()

    log.info("Gratia collector to use: %s" % Gratia.Config.get_SOAPHost())

    for record in record_list:
        log.info("Sending record for probe %s in site %s to Gratia: %s."% \
            (probeName, site, Gratia.Send(record)))

    os._exit(0)

def main():
    cp = None
    for filename in ["$HOME/.cms_storage_record.conf",
            "/etc/cms_storage_record.conf"]:
        filename = os.path.expandvars(filename)
        if os.path.exists(filename):
            cp = config_file(filename)
            break
    if cp == None:
        print "Could not find cms_storage_record.conf in /etc!"
        sys.exit(1)

    do_cms_se_info(cp)

if __name__ == '__main__':
    signal.alarm(5*60)
    main()

