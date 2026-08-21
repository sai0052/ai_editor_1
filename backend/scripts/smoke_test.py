import json
import time
import urllib.request
from pathlib import Path

print("health", urllib.request.urlopen("http://127.0.0.1:8000/api/health").read().decode())

boundary = "----autocut"
sample = Path("storage/temp/sample.mp4").read_bytes()
header = (
    f"--{boundary}\r\n"
    'Content-Disposition: form-data; name="file"; filename="sample.mp4"\r\n'
    "Content-Type: video/mp4\r\n\r\n"
).encode()
body = header + sample + f"\r\n--{boundary}--\r\n".encode()
req = urllib.request.Request(
    "http://127.0.0.1:8000/api/videos/upload",
    data=body,
    method="POST",
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
)
upload = json.loads(urllib.request.urlopen(req).read().decode())
print("upload", upload["video_id"], upload["metadata"]["duration"])
vid = upload["video_id"]

payload = {
    "video_id": vid,
    "options": {
        "noise": {"enabled": True, "strength": "medium"},
        "silence": {
            "enabled": True,
            "preset": "balanced",
            "min_silence_ms": None,
            "keep_silence_ms": None,
        },
        "captions": {
            "enabled": False,
            "language": "auto",
            "style": "clean",
            "font": "Arial",
            "font_size": 48,
            "position": "bottom",
            "color": "#FFFFFF",
            "background": "#000000AA",
            "stroke": "#000000",
            "highlight_color": "#FFD166",
            "burn_in": True,
        },
        "color": {
            "enabled": True,
            "preset": "cinematic",
            "auto_color": False,
            "brightness": 0,
            "contrast": 1,
            "saturation": 1,
            "highlights": 0,
            "shadows": 0,
            "temperature": 0,
        },
        "pauses": {"enabled": False, "aggressiveness": 0.5},
        "reframe": {"enabled": False, "aspect": "9:16"},
        "jump_cuts": {"enabled": False, "aggressiveness": 0.4},
        "filler": {"enabled": False, "mode": "remove"},
    },
    "export": {"resolution": "original", "format": "mp4", "fps": "original", "quality": "high"},
}
req = urllib.request.Request(
    "http://127.0.0.1:8000/api/jobs",
    data=json.dumps(payload).encode(),
    method="POST",
    headers={"Content-Type": "application/json"},
)
job = json.loads(urllib.request.urlopen(req).read().decode())
jid = job["job_id"]
print("job", jid, job["status"])

for i in range(80):
    time.sleep(0.4)
    st = json.loads(urllib.request.urlopen(f"http://127.0.0.1:8000/api/jobs/{jid}").read().decode())
    print(i, st["status"], round(st["progress"], 1), [(s["id"], s["status"]) for s in st["stages"]])
    if st["status"] in ("completed", "failed"):
        print("summary", st.get("summary"))
        print("error", st.get("error"))
        if st["status"] == "completed":
            data = urllib.request.urlopen(f"http://127.0.0.1:8000/api/jobs/{jid}/result").read()
            print("result bytes", len(data))
        break
