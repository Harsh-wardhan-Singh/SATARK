import ast
import importlib
import os
import sys
from pathlib import Path

backend_dir = Path(r"c:\Users\sitak\SATARK\backend")
sys.path.insert(0, str(backend_dir))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
try:
    django.setup()
    print("Django setup successful.")
except Exception as e:
    print(f"Django setup error: {e}")

syntax_errors = []
import_errors = []

for root, dirs, files in os.walk(backend_dir):
    # Skip .venv or cache
    if ".venv" in root or "__pycache__" in root or "migrations" in root:
        continue
    for file in files:
        if file.endswith(".py"):
            full_path = Path(root) / file
            # 1. Check AST syntax
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    source = f.read()
                ast.parse(source, filename=str(full_path))
            except Exception as e:
                syntax_errors.append((str(full_path), str(e)))

print(f"Checked syntax across backend. Errors found: {len(syntax_errors)}")
for p, err in syntax_errors:
    print(f"SYNTAX ERROR in {p}: {err}")

# Check importability of all backend modules
module_count = 0
for root, dirs, files in os.walk(backend_dir):
    if ".venv" in root or "__pycache__" in root or "migrations" in root or "tests" in root:
        continue
    for file in files:
        if file.endswith(".py"):
            rel_path = Path(root).relative_to(backend_dir)
            if file == "__init__.py":
                mod_name = ".".join(rel_path.parts)
            else:
                mod_name = ".".join(rel_path.parts + (file[:-3],))
            if not mod_name:
                continue
            module_count += 1
            try:
                importlib.import_module(mod_name)
            except Exception as e:
                import_errors.append((mod_name, str(e)))

print(f"Checked imports for {module_count} modules. Import errors: {len(import_errors)}")
for mod, err in import_errors:
    print(f"IMPORT ERROR in {mod}: {err}")
