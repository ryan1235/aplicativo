import re

with open(r'c:\Users\ryanl\OneDrive\Desktop\aplicativo\qt_controllers.py', 'r', encoding='utf-8') as f:
    code = f.read()

nav_target = '''                {"key": "profile", "labelKey": "nav.profile", "icon": "user", "section": "core"},'''
code = code.replace(nav_target, "")

with open(r'c:\Users\ryanl\OneDrive\Desktop\aplicativo\qt_controllers.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Nav patched")
