import json
import statistics
import sys
import time
import urllib.request

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/v1/predict"
ROW = {
    "Department": "Business Administration", "Gender": "Male",
    "HSC": 4.17, "SSC": 4.84, "Income": "Low (Below 15,000)",
    "Hometown": "Village", "Computer": 3, "Preparation": "More than 3 Hours",
    "Gaming": "0-1 Hour", "Attendance": "80%-100%", "Job": "No",
    "English": 3, "Extra": "Yes", "Semester": "6th", "Last": 3.22,
}

WARMUP, N = 20, 200
lat = []
for i in range(WARMUP + N):
    t0 = time.perf_counter()
    req = urllib.request.Request(URL, data=json.dumps(ROW).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        resp.read()
    lat.append((time.perf_counter() - t0) * 1000)
lat = lat[WARMUP:]  # первые запросы медленные из-за прогрева — выбрасываем

def pct(p): return lat[min(len(lat) - 1, int(len(lat) * p))]

print(f"URL={URL}")
print(f"n={len(lat)} min={min(lat):.2f} p50={pct(.5):.2f} p90={pct(.9):.2f} "
      f"p95={pct(.95):.2f} p99={pct(.99):.2f} max={max(lat):.2f} "
      f"mean={statistics.fmean(lat):.2f} (ms)")