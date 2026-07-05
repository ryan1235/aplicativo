with open('qml/components/MapView.qml', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.split('\n')

def check_braces(limit):
    t = '\n'.join(lines[:limit])
    import re
    # remove strings
    t = re.sub(r'\"([^\\\"]|\\.)*\"', '', t)
    t = re.sub(r'\'([^\\\']|\\.)*\'', '', t)
    # remove comments
    t = re.sub(r'//.*', '', t)
    t = re.sub(r'/\*.*?\*/', '', t, flags=re.DOTALL)
    o = t.count('{')
    c = t.count('}')
    print(f'Lines: {limit}, Open: {o}, Close: {c}, Diff: {o - c}')

check_braces(1917)
check_braces(1918)
check_braces(1919)
