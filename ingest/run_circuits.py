"""Run the circuit extractor over every Hyd.Ckt PDF under a root; write JSON + coverage report.
usage: python run_circuits.py <root> <out_dir>"""
import glob, json, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from docsearch_ingest.circuit import extract_circuit, LABELS

root, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
files = sorted(f for f in glob.glob(os.path.join(root, "**", "*.pdf"), recursive=True)
               if "hyd.ckt" in os.path.basename(f).lower())
results = []
for f in files:
    t = time.time()
    try:
        r = extract_circuit(f)
    except Exception as e:  # keep going; report
        r = {"specs": {}, "terminations": [], "notes": [], "warnings": [f"EXCEPTION {type(e).__name__}: {e}"]}
    r["file"] = os.path.relpath(f, root)
    r["seconds"] = round(time.time() - t, 1)
    results.append(r)
    print(f"{r['seconds']:5.1f}s  {len(r['specs']):2d}/{len(LABELS)} specs  {len(r['terminations']):2d} ports  {len(r['notes'])} notes  {r['file']}")
json.dump(results, open(os.path.join(out, "circuits.json"), "w"), indent=1)

# per-field coverage
print("\nFIELD COVERAGE (non-empty / total)")
for k in [k for k in LABELS if k != "project_name"]:
    n = sum(1 for r in results if k in r["specs"])
    print(f"  {k:28s} {n:3d}/{len(results)}")
print("with >=1 termination row:", sum(1 for r in results if r["terminations"]), "/", len(results))
print("with warnings:", [ (r['file'], r['warnings']) for r in results if r['warnings']])
