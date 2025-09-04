import os, glob, requests

API = "http://127.0.0.1:8000/ingest"
FOLDER = r"C:\Users\yomse\eventsdc-doc-poc\data\uploads"

files = glob.glob(os.path.join(FOLDER, "*.*"))
assert files, f"No files in {FOLDER}. Put PDFs/DOCX/PPTX/TXT there."

ok, fail = 0, 0
for p in files:
    with open(p, "rb") as f:
        resp = requests.post(API, files={"file": (os.path.basename(p), f)})
        if resp.status_code == 200 and "Ingested" in resp.text:
            ok += 1
        else:
            fail += 1
            print("FAILED:", p, resp.status_code, resp.text[:200])
print(f"Done. OK={ok}, FAIL={fail}, total={len(files)}")
