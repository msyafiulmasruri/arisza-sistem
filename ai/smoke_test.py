"""Uji cepat layanan setelah di-deploy (jalankan dari laptop, bukan di Space).

Contoh:
  python smoke_test.py https://NAMAKAMU-NAMASPACE.hf.space KUNCI_API
Jika Space bersifat private, tambahkan token Hugging Face:
  python smoke_test.py https://... KUNCI_API --hf-token hf_xxx
Tambahkan --tanpa-llama bila hanya ingin menguji model utama.
"""
import json
import sys
import time
import urllib.request

TEKS_UJI = [
    "Tempatnya nyaman banget, bukunya lengkap dan suasananya tenang",
    "Petugasnya ramah dan membantu mencari buku",
    "Kopinya enak dan harganya terjangkau",
    "Jam buka sampai jam berapa ya?",
    "Lokasinya di mana dan apakah ada parkir?",
    "Ada acara diskusi buku tiap bulan",
    "Ruangannya panas, ACnya kurang dingin saat ramai",
    "Tempat duduknya sering penuh dan susah cari kursi",
    "Pelayanannya lama dan kurang ramah",
]


def minta(url, kunci, hf_token=None, data=None):
    header = {"X-API-Key": kunci, "Content-Type": "application/json"}
    if hf_token:
        header["Authorization"] = f"Bearer {hf_token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=header, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    basis, kunci = sys.argv[1].rstrip("/"), sys.argv[2]
    hf_token = sys.argv[sys.argv.index("--hf-token") + 1] if "--hf-token" in sys.argv else None
    pakai_llama = "--tanpa-llama" not in sys.argv

    print("1) /health")
    print(json.dumps(minta(f"{basis}/health", kunci, hf_token), indent=2, ensure_ascii=False))

    print("\n2) /predict")
    t0 = time.perf_counter()
    hasil = minta(f"{basis}/predict", kunci, hf_token, {"texts": TEKS_UJI})
    print(f"waktu: {time.perf_counter() - t0:.2f} detik untuk {len(TEKS_UJI)} teks")
    for r in hasil["results"]:
        print(f"  {r['sentiment']:<9} {r['confidence']}  | {r['text'][:60]}")

    if not pakai_llama:
        return

    print("\n3) /interpret (pekerjaan latar belakang)")
    items = [{"text": r["text"], "label": r["sentiment"], "confidence": r["confidence"]}
             for r in hasil["results"] if r["status"] == "ok"]
    job = minta(f"{basis}/interpret", kunci, hf_token, {"media": "Uji", "items": items})
    print("job:", job)
    t0 = time.perf_counter()
    while True:
        time.sleep(10)
        status = minta(f"{basis}/jobs/{job['job_id']}", kunci, hf_token)
        print(f"  [{time.perf_counter() - t0:6.0f} dtk] status: {status['status']}")
        if status["status"] in ("done", "failed"):
            break
    print(json.dumps(status, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
