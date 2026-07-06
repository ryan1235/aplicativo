import ast
import os
import re

def split_file():
    with open('qt_controllers.py', 'r', encoding='utf-8') as f:
        source = f.read()
    
    lines = source.splitlines()
    tree = ast.parse(source)
    
    # Identify nodes
    classes = []
    functions = []
    imports = []
    other = []
    
    for node in tree.body:
        start = node.lineno - 1
        end = node.end_lineno
        block = lines[start:end]
        if isinstance(node, ast.ClassDef):
            classes.append((node.name, start, end, block))
        elif isinstance(node, ast.FunctionDef):
            functions.append((node.name, start, end, block))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append((start, end, block))
        else:
            other.append((start, end, block))
            
    os.makedirs('controllers', exist_ok=True)
    os.makedirs('core', exist_ok=True)
    
    # 1. common.py (Imports + Others + Functions)
    # We will just write all non-class lines, preserving order.
    # Actually, let's just make `controllers/common.py` which contains everything except classes.
    # But wait, there might be decorators or comments before classes. 
    # Let's extract exactly the class ranges.
    
    class_ranges = []
    for cls in classes:
        # include preceding decorators
        start = cls[1]
        # try to find decorators
        while start > 0 and lines[start-1].strip().startswith('@'):
            start -= 1
        class_ranges.append((start, cls[2], cls[0], lines[start:cls[2]]))
        
    class_ranges.sort(key=lambda x: x[0])
    
    # 2. Write common.py
    common_lines = []
    current_idx = 0
    for cr in class_ranges:
        common_lines.extend(lines[current_idx:cr[0]])
        current_idx = cr[1]
    common_lines.extend(lines[current_idx:])
    
    with open('controllers/common.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(common_lines))
        
    # 3. Write individual class files
    # To ensure they have imports, we prepend all imports from qt_controllers.py
    import_text = []
    for imp in imports:
        import_text.extend(imp[2])
        
    # A generic header for each class
    header = import_text + ["", "from .common import *", ""]
    
    class_modules = []
    for cr in class_ranges:
        cname = cr[2]
        cblock = cr[3]
        filename = re.sub(r'(?<!^)(?=[A-Z])', '_', cname).lower() + '.py'
        
        filepath = os.path.join('controllers', filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(header + cblock) + '\n')
            
        class_modules.append((cname, filename[:-3]))
        
    # 4. Write new qt_controllers.py
    new_qt_controllers = []
    for cname, mod in class_modules:
        new_qt_controllers.append(f"from controllers.{mod} import {cname}")
        
    # Export ControllerRegistry if it was there
    new_qt_controllers.append("\n__all__ = [")
    for cname, _ in class_modules:
        new_qt_controllers.append(f"    '{cname}',")
    new_qt_controllers.append("]\n")
    
    with open('qt_controllers.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_qt_controllers))
        
    print(f"Split {len(classes)} classes into controllers/ directory.")

if __name__ == '__main__':
    split_file()
