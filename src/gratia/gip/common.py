
def getGipDBConn(cp):
    MySQLdb = __import__("MySQLdb")
    info = {}
    host = cp_get(cp, "gip_db", "dbhost", "localhost")
    if host != "localhost":
        info["host"] = host
    user = cp_get(cp, "gip_db", "dbuser", None)
    if user != None:
        info["user"] = user
    port = cp_get(cp, "gip_db", "dbport", None)
    if port != None:
        info["port"] = int(port)
    info["db"] = cp_get(cp, "gip_db", "db", "gip")
    passwd = cp_get(cp, "gip_db", "dbpasswd", None)
    if passwd != None:
        info["passwd"] = passwd
    return MySQLdb.connect(**info)

def cp_get(cp, section, option, default):
    try:
        return cp.get(section, option)
    except:
        return default

def findCE(vo_entry, ce_entries):
    for ce_entry in ce_entries:
        if ce_entry.dn[0] == vo_entry.glue["ChunkKey"]:
            return ce_entry
    raise ValueError("Corresponding CE not found for VO entry:\n%s" % vo_entry)

def join_FK(item, join_list, join_attr, join_fk_name="ForeignKey"):
    item_fk = item.glue[join_fk_name]
    for entry in join_list:
        test_val = "Glue%s=%s" % (join_attr, entry.glue[join_attr])
        if test_val == item_fk:
            return entry
    raise ValueError("Unable to find matching entry in list.")

