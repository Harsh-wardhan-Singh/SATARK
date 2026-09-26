import ast
from pathlib import Path

engine_file = Path(r"c:\Users\sitak\SATARK\backend\simulation\engine.py")
code = engine_file.read_text(encoding="utf-8")
tree = ast.parse(code)

lines = code.splitlines()
print(f"Total lines in engine.py: {len(lines)}")

methods = []
for node in tree.body:
    if isinstance(node, ast.ClassDef) and node.name == "SimulationEngine":
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append((item.name, item.lineno, getattr(item, 'end_lineno', 0)))

print(f"Total methods in SimulationEngine: {len(methods)}")
for name, start, end in methods:
    print(f"  {name:40s} lines {start:4d} - {end:4d} ({end - start + 1:3d} lines)")
