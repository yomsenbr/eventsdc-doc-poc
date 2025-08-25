import time, requests

def time_get(url, params=None):
    t0 = time.perf_counter()
    r = requests.get(url, params=params, timeout=60)
    ms = round((time.perf_counter()-t0)*1000)
    return r.status_code, ms, r.json()

BASE = "http://127.0.0.1:8000"
for path, params in [
    ("/search/hybrid", {"q":"invoice policy","k":5}),
    ("/chat", {"q":"what is our refund policy?","k":5}),
]:
    s, ms, _ = time_get(BASE+path, params)
    print(f"{path} {s} in {ms} ms")
