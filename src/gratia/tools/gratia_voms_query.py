
import os

from pkg_resources import resource_filename

from graphtool.base.xml_config import XmlConfig
from gratia.voms import mapVos

def main():
    db_sec = os.path.expandvars("$HOME/dbinfo/DBSecurity.xml")
    if not os.path.exists(db_sec):
        db_sec = os.path.expandvars("$DBSECURITY_LOCATION")
    if not os.path.exists(db_sec):
        db_sec = os.path.expandvars("/etc/DBSecurity.xml")
    if not os.path.exists(db_sec):
        db_sec = os.path.expandvars("/etc/DBParam.xml")
    x = XmlConfig(file=db_sec)
    filename = resource_filename("gratia.config", "gratia_data_queries.xml")
    x = XmlConfig(file=filename)
    conn_man = x.globals['GratiaSecurityDB']
    gratia_data = x.globals['GratiaDataQueries']
    conn_obj = conn_man.get_connection(None)
    conn = conn_obj.get_connection()
    curs = conn.cursor()
    for vo, members in mapVos().items():
        try:
            gratia_voname = gratia_data.vo_lookup(vo=vo)[0][0][0]
        except:
            gratia_voname = 'UNKNOWN'
        print "VO: %s, Gratia VO: %s" % (vo, gratia_voname)
        try:
            curs.execute("DELETE FROM VOMembers where vo=?", (vo,))
        except TypeError:
            curs.execute("DELETE FROM VOMembers where vo=%s", (vo,))
        for member in members:
            try:
                curs.execute("INSERT INTO VOMembers VALUES (?, ?, ?)", (vo, member[0], member[1]))
            except TypeError:
                curs.execute("INSERT INTO VOMembers VALUES (%s, %s, %s)", (vo, member[0], member[1]))
    conn.commit()

if __name__ == '__main__':
    main()

