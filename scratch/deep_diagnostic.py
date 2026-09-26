import os
import sys
import re
import ast
import json
from pathlib import Path

ROOT = Path(r"c:\Users\sitak\SATARK")
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

print("=" * 80)
print("DEEP CODEBASE DIAGNOSTIC AUDIT")
print("=" * 80)

# Check 1: Test coverage mapping in backend
tests_dir = BACKEND / "tests"
test_files = list(tests_dir.glob("test_*.py"))
print(f"\n1. Pytest suite: {len(test_files)} test files found.")
for tf in sorted(test_files):
    print(f"   - {tf.name}")

# Modules in backend:
backend_modules = []
for p in BACKEND.rglob("*.py"):
    if "tests" in str(p) or "__pycache__" in str(p) or "migrations" in str(p) or "manage.py" in str(p):
        continue
    rel = p.relative_to(BACKEND)
    backend_modules.append(rel)

print(f"\n2. Total active backend modules: {len(backend_modules)}")

# Check 2: Check backend modules imported in test files
test_content = "\n".join(tf.read_text(encoding="utf-8") for tf in test_files)
untested_modules = []
for m in backend_modules:
    stem = m.stem
    if stem == "__init__":
        continue
    # check if stem is mentioned in test_content
    if not re.search(r"\b" + stem + r"\b", test_content):
        untested_modules.append(str(m))

print(f"\n3. Backend modules with NO direct mention in pytest suite ({len(untested_modules)}):")
for um in sorted(untested_modules):
    print(f"   - {um}")

# Check 3: Check engine.py size and breakdown
engine_path = BACKEND / "simulation" / "engine.py"
engine_lines = engine_path.read_text(encoding="utf-8").splitlines()
print(f"\n4. engine.py current line count: {len(engine_lines)}")

# Check 4: Check optimizer.py interaction with pipeline and propagators
opt_path = BACKEND / "decision" / "optimizer.py"
opt_text = opt_path.read_text(encoding="utf-8")
print(f"\n5. optimizer.py evaluation:")
print(f"   - Imports SimulationEngine: {'SimulationEngine' in opt_text}")
print(f"   - Uses SimulationProvider callback: {'SimulationProvider' in opt_text}")

# Check 5: Check api views for state leak / error handling
views_path = BACKEND / "api" / "views.py"
views_text = views_path.read_text(encoding="utf-8")
print(f"\n6. views.py audit:")
print(f"   - _active_engine reset mechanism: {'def reset' in views_text or '_active_engine = None' in views_text}")
# count how many times _active_engine = None occurs
print(f"   - _active_engine resets count: {views_text.count('_active_engine = None')}")

# Check 6: Check frontend files for hardcoded endpoints or orphaned state
print(f"\n7. Frontend audit:")
for ts_file in FRONTEND.rglob("*.ts*"):
    if "node_modules" in str(ts_file) or "dist" in str(ts_file):
        continue
    text = ts_file.read_text(encoding="utf-8")
    # Check for localhost:8000
    if "localhost:8000" in text:
        print(f"   - Hardcoded localhost:8000 in {ts_file.relative_to(FRONTEND)}")
    # Check for /data/
    if "/data/" in text:
        print(f"   - Static /data/ reference in {ts_file.relative_to(FRONTEND)}")

# Check 7: Dead files in frontend public
print(f"\n8. Frontend public directory audit:")
pub_data = FRONTEND / "public" / "data"
if pub_data.exists():
    for f in pub_data.iterdir():
        size = f.stat().st_size
        print(f"   - {f.name} ({size} bytes)")

print("\n" + "=" * 80)
