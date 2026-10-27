const BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const KUNCI = "arisza_admin_key";

export const simpanKunci = (k) => sessionStorage.setItem(KUNCI, k);
export const hapusKunci = () => sessionStorage.removeItem(KUNCI);
export const adaKunci = () => !!sessionStorage.getItem(KUNCI);

export class GalatApi extends Error {
  constructor(pesan, status) {
    super(pesan);
    this.status = status;
  }
}

async function minta(path, { method = "GET", body, kunci } = {}) {
  const headers = { "X-Admin-Key": kunci ?? sessionStorage.getItem(KUNCI) ?? "" };
  if (body && !(body instanceof FormData)) headers["Content-Type"] = "application/json";
  let res;
  try {
    res = await fetch(BASE + path, {
      method,
      headers,
      body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new GalatApi("Backend tidak dapat dihubungi. Periksa alamat backend dan koneksi internet.", 0);
  }
  if (!res.ok) {
    let pesan = `Permintaan gagal (${res.status}).`;
    try {
      const j = await res.json();
      if (typeof j.detail === "string") pesan = j.detail;
    } catch {}
    throw new GalatApi(pesan, res.status);
  }
  return res.json();
}

// Gambar dan berkas membutuhkan header kunci, jadi diambil lewat fetch lalu dijadikan alamat sementara.
async function mintaBerkas(path) {
  let res;
  try {
    res = await fetch(BASE + path, { headers: { "X-Admin-Key": sessionStorage.getItem(KUNCI) ?? "" } });
  } catch {
    throw new GalatApi("Backend tidak dapat dihubungi. Periksa alamat backend dan koneksi internet.", 0);
  }
  if (!res.ok) {
    let pesan = `Permintaan gagal (${res.status}).`;
    try {
      const j = await res.json();
      if (typeof j.detail === "string") pesan = j.detail;
    } catch {}
    throw new GalatApi(pesan, res.status);
  }
  return res.blob();
}

const qs = (o) => {
  const p = new URLSearchParams();
  Object.entries(o).forEach(([k, v]) => v !== "" && v != null && p.set(k, v));
  const t = p.toString();
  return t ? `?${t}` : "";
};

export const api = {
  masuk: (kunci) => minta("/api/auth", { kunci }),
  ringkasan: () => minta("/api/summary"),
  infoWordcloud: (media) => minta(`/api/media/${encodeURIComponent(media)}/wordclouds`),
  gambarWordcloud: async (media, label) =>
    URL.createObjectURL(await mintaBerkas(`/api/media/${encodeURIComponent(media)}/wordcloud/${label}`)),
  tabel: (f) => minta(`/api/responses${qs(f)}`),
  unduhCsv: async (f) => {
    const blob = await mintaBerkas(`/api/responses/export${qs(f)}`);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "tanggapan.csv";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  },
  lengkapi: () => minta("/api/maintenance/lengkapi", { method: "POST" }),
  interpretasi: (media) => minta(`/api/media/${encodeURIComponent(media)}/interpretation`),
  jalankan: (media) => minta(`/api/media/${encodeURIComponent(media)}/interpret`, { method: "POST" }),
  ulangiRun: (id) => minta(`/api/runs/${id}/retry`, { method: "POST" }),
  batch: () => minta("/api/batches"),
  ulangiBatch: (id) => minta(`/api/batches/${id}/retry`, { method: "POST" }),
  impor: (berkas, mediaBawaan) => {
    const f = new FormData();
    f.append("file", berkas);
    f.append("media_bawaan", mediaBawaan || "");
    return minta("/api/import", { method: "POST", body: f });
  },
};
