import os
import sys
import re
import ast
import json
from pathlib import Path

ROOT = Path(r"c:\Users\sitak\SATARK")
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

findings = {
    "syntax_errors": [],
    "earthquake_remnants": [],
    "engine_legacy_methods": [],
    "api_frontend_mismatches": [],
    "safezone_and_shelter_issues": [],
    "optimizer_divergence": [],
    "state_isolation_leaks": [],
    "todo_fixme_items": [],
    "misc_discrepancies": []
}

# 1. Check for any remaining earthquake remnants across both backend and frontend
for path in list(BACKEND.rglob("*.py")) + list(FRONTEND.rglob("*.ts*")):
    if "node_modules" in str(path) or ".venv" in str(path) or "dist" in str(path):
        continue
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        matches = [m.start() for m in re.finditer(r"\bearthquake\b", content, re.IGNORECASE)]
        if matches:
            # check lines
            lines = content.splitlines()
            for idx, line in enumerate(lines):
                if re.search(r"\bearthquake\b", line, re.IGNORECASE):
                    findings["earthquake_remnants"].append((str(path.relative_to(ROOT)), idx + 1, line.strip()))
    except Exception as e:
        findings["syntax_errors"].append((str(path), str(e)))

# 2. Check engine.py for dead legacy methods from before pipeline extraction
engine_file = BACKEND / "simulation" / "engine.py"
if engine_file.exists():
    try:
        engine_ast = ast.parse(engine_file.read_text(encoding="utf-8"))
        engine_class = None
        for node in engine_ast.body:
            if isinstance(node, ast.ClassDef) and node.name == "SimulationEngine":
                engine_class = node
                break
        if engine_class:
            method_names = [m.name for m in engine_class.body if isinstance(m, ast.FunctionDef)]
            # Check which methods are actually called within engine.py
            engine_code = engine_file.read_text(encoding="utf-8")
            for m in method_names:
                # count occurrences of self.m or m(
                count = len(re.findall(r"\b" + m + r"\b", engine_code))
                if count <= 1 and not m.startswith("__"):
                    findings["engine_legacy_methods"].append(m)
    except Exception as e:
        findings["syntax_errors"].append(("engine.py", str(e)))

# 3. Check optimizer.py for how it executes simulation vs pipeline
optimizer_file = BACKEND / "decision" / "optimizer.py"
if optimizer_file.exists():
    opt_code = optimizer_file.read_text(encoding="utf-8")
    if "_build_simulation_evaluation" in opt_code or "engine.step(" in opt_code or "pipeline" in opt_code:
        findings["optimizer_divergence"].append("Optimizer interaction pattern: " + ("Uses pipeline" if "pipeline" in opt_code else "Does NOT use pipeline directly"))

# 4. Check API views and singleton engine state
views_file = BACKEND / "api" / "views.py"
if views_file.exists():
    v_code = views_file.read_text(encoding="utf-8")
    if "_active_engine" in v_code:
        findings["state_isolation_leaks"].append("views.py maintains module-level `_active_engine = None` which persists across requests and tests")

# 5. Check frontend SafeZone and shelter integration
city_scene = FRONTEND / "src" / "components" / "twin" / "CityScene.tsx"
zone_renderer = FRONTEND / "src" / "city" / "zones" / "ZoneRenderer.ts"
world_api = FRONTEND / "src" / "api" / "worldApi.ts"

if city_scene.exists() and zone_renderer.exists():
    cs_code = city_scene.read_text(encoding="utf-8")
    zr_code = zone_renderer.read_text(encoding="utf-8")
    wa_code = world_api.read_text(encoding="utf-8") if world_api.exists() else ""
    findings["safezone_and_shelter_issues"].append({
        "world_api_fetchSafeZones": "fetchSafeZones" in wa_code,
        "city_scene_setSafeZones": "setSafeZones" in cs_code,
        "zone_renderer_safe_zones": "safeZones" in zr_code or "setSafeZones" in zr_code
    })

# 6. Check TODOs and FIXMEs
for path in list(BACKEND.rglob("*.py")) + list(FRONTEND.rglob("*.ts*")):
    if "node_modules" in str(path) or ".venv" in str(path) or "dist" in str(path):
        continue
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()
        for idx, line in enumerate(lines):
            if "TODO" in line or "FIXME" in line:
                findings["todo_fixme_items"].append((str(path.relative_to(ROOT)), idx + 1, line.strip()))
    except Exception:
        pass

print(json.dumps(findings, indent=2))
