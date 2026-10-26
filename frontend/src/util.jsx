import { useEffect, useRef } from "react";

export const NAMA = { positive: "Positif", neutral: "Netral", negative: "Negatif" };
export const URUTAN = ["positive", "neutral", "negative"];
export const STATUS = {
  waiting: "Menunggu", queued: "Menunggu", running: "Diproses", done: "Selesai", failed: "Gagal",
};

export const tanggal = (x) =>
  x ? new Date(x).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" }) : "-";

export const persen = (n, total) => (total ? Math.round((n / total) * 1000) / 10 : 0);

export const aktif = (status) => status === "queued" || status === "running";

// Menjalankan fungsi berkala selama `jalan` bernilai true.
export function useBerkala(fn, jalan, ms = 5000) {
  const ref = useRef(fn);
  ref.current = fn;
  useEffect(() => {
    if (!jalan) return undefined;
    const id = setInterval(() => ref.current(), ms);
    return () => clearInterval(id);
  }, [jalan, ms]);
}

export function BarSentimen({ data }) {
  const total = data.positive + data.neutral + data.negative;
  if (!total) return <div className="bar kosong" aria-label="Belum ada data" />;
  return (
    <div className="bar" role="img"
      aria-label={URUTAN.map((l) => `${NAMA[l]} ${persen(data[l], total)} persen`).join(", ")}>
      {URUTAN.map((l) =>
        data[l] ? (
          <span key={l} className={`seg ${l}`} style={{ flexGrow: data[l] }}>
            {persen(data[l], total) >= 8 ? `${persen(data[l], total)}%` : ""}
          </span>
        ) : null
      )}
    </div>
  );
}

export function Pesan({ jenis = "info", children }) {
  if (!children) return null;
  return <p className={`pesan ${jenis}`} role={jenis === "galat" ? "alert" : "status"}>{children}</p>;
}
