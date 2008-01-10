
def displayName(*args, **kw):
    dn = args[0]
    parts = dn.split('/')
    display = 'Unknown'
    for part in parts:
        if len(part) == 0:
            continue
        try:
            attr, val = part.split('=', 1)
        except:
            continue
        if attr == 'CN':
            display = val
    try:
        parts = display.split()
        dummy = int(parts[-1])
        display = display[:-len(parts[-1])-1]
    except:
        pass
    proper = ''
    for parts in display.split():
        proper += parts[0].upper() + parts[1:].lower() + ' '
    return proper[:-1]
 
