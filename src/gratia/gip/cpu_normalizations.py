
import urllib2
from xml.dom.minidom import parse

OIM_url = 'http://myosg.grid.iu.edu/misccpuinfo/xml?datasource=cpuinfo&count_sg_1=on'

def get_cpu_normalizations(url=OIM_url):
    try:
        dom = parse(urllib2.urlopen(url))
    except:
        raise Exception("Unable to parse CPU XML data from OIM!")
    results = {}
    for cpu_dom in dom.getElementsByTagName("CPUInfo"):
        name_dom = cpu_dom.getElementsByTagName("Name")
        try:
            name = str(name_dom[0].firstChild.data)
        except:
            continue
        normalization_dom = cpu_dom.getElementsByTagName( \
            "NormalizationConstant")
        try:
            normalization = float(str(normalization_dom[0].firstChild.data))
        except:
            continue
        normalization *= 1000
        normalization = int(round(normalization))
        notes_dom= cpu_dom.getElementsByTagName("Notes")
        try:
            notes = str(notes_dom[0].firstChild.data)
        except:
            continue
        results[name] = (normalization, 0, notes)
    return results

if __name__ == '__main__':
    results = get_cpu_normalizations()
    for key, val in results.items():
        print key, val

