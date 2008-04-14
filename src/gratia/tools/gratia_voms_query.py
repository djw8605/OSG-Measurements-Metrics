
import os

from pkg_resources import resource_filename

from graphtool.base.xml_config import XmlConfig
from gratia.voms import mapVos

def main():
    db_sec = os.path.expandvars("$HOME/dbinfo/DBSecurity.xml")
    x = XmlConfig(file=db_sec)
    filename = resource_filename("gratia.config", "gratia_data_queries.xml")
    x = XmlConfig(file=filename)
    conn_man = x.globals['GratiaSecurityDB']
    gratia_data = x.globals['GratiaDataQueries']
    conn_obj = conn_man.get_connection(None)
    conn = conn_obj.get_connection()
    curs = conn.cursor()
    for vo, members in mapVos().items():
        gratia_voname = gratia_data.vo_lookup(vo=vo)[0][0][0]
        print "VO: %s, Gratia VO: %s" % (vo, gratia_voname)
        curs.execute("DELETE FROM VOMembers where vo=?", (vo,))
        for member in members:
            curs.execute("INSERT INTO VOMembers VALUES (?, ?)", (vo, member))
    conn.commit()

if __name__ == '__main__':
    main()

