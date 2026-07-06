import re

with open(r'c:\Users\ryanl\OneDrive\Desktop\aplicativo\qt_controllers.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Pattern to find the injected code block
pattern = r'''    @Slot\(str\)
    def fetchProfile\(self, user_id: str = ""\) -> None:.*?threading\.Thread\(target=run, daemon=True\)\.start\(\)\n\n'''

# Remove ALL occurrences of the injected block
code = re.sub(pattern, "", code, flags=re.DOTALL)

# Also fix the payload kwarg in the pattern if any was left
# But we just stripped it all.

with open(r'c:\Users\ryanl\OneDrive\Desktop\aplicativo\qt_controllers.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Duplicates removed.")
