
import ConfigParser
import types

cp = ConfigParser.ConfigParser()
cp.read('gip.conf')

cpu_dict = eval(cp.get('cpu_count', 'specint2k'))

for key, val in cpu_dict.items():
    if isinstance(val, types.TupleType):
        score = val[0]
        notes = 'kSI2K value; %s' % val[1]
    else:
        score = val
        notes = 'kSI2K value'
    score /= 1000.0
    print 'INSERT INTO cpu_info SET name="%s", normalization_constant=%.3f, notes="%s"' % (key, score, notes)
