import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import { NAMA, Pesan, STATUS, aktif, tanggal, useBerkala } from "./util.jsx";

const TAHAP = [
  ["positive", "Pola opini positif"],
  ["neutral", "Pola opini netral"],
  ["negative", "Pola opini negatif"],
  ["saran", "Saran tindak lanjut"],
];

function Tahap({ run }) {
  const per = Object.fromEntries(run.tahap.map((t) => [t.stage, t]));
  return (
    <ol className="tahap">
      {TAHAP.map(([id, judul]) => {
        const t = per[id];
        return (
          <li key={id} className={`t-${t.status}`}>
            <div className="t-kepala">
              <h3>{judul}</h3>
              <span className="chip">{STATUS[t.status]}</span>
              {t.status === "done" && t.duration > 0 && <span className="redup">{Math.round(t.duration)} detik</span>}
              {id !== "saran" && t.status === "done" && t.texts_total > 0 && (
                <span className="redup">{t.texts_used} dari {t.texts_total} teks dipakai</span>
              )}
            </div>
            {t.status === "running" && <p className="redup">Llama sedang menyusun {judul.toLowerCase()}…</p>}
            {t.status === "failed" && <Pesan jenis="galat">{t.error}</Pesan>}
            {t.status === "done" && <p className="hasil">{t.result}</p>}
          </li>
        );
      })}
    </ol>
  );
}

export default function Interpretasi({ media, terpilih, setTerpilih, muatUlang, bukaImpor }) {
  const [data, setData] = useState(null);
  const [galat, setGalat] = useState("");
  const [sibuk, setSibuk] = useState(false);

  const muat = useCallback(async () => {
    if (!terpilih) return;
    try {
      setData(await api.interpretasi(terpilih));
      setGalat("");
    } catch (e) {
      setGalat(e.message);
    }
  }, [terpilih]);

  useEffect(() => { setData(null); muat(); }, [muat]);

  const run = data?.terbaru;
  const jalan = !!run && aktif(run.status);
  useBerkala(async () => { await muat(); muatUlang(); }, jalan, 5000);

  if (!media) return <p className="redup">Memuat…</p>;
  if (!media.length) {
    return (
      <section className="kosong-blok">
        <h2>Belum ada media</h2>
        <p>Interpretasi disusun per media setelah data diimpor.</p>
        <button onClick={bukaImpor}>Impor data</button>
      </section>
    );
  }

  const info = media.find((m) => m.media === terpilih);
  const gagal = run?.status === "failed";
  const selesaiTerbaru = run?.status === "done";
  const sebelumnya = data?.terakhir_selesai;

  async function mulai(fn) {
    setSibuk(true);
    setGalat("");
    try {
      await fn();
      await muat();
      muatUlang();
    } catch (e) {
      setGalat(e.message);
    } finally {
      setSibuk(false);
    }
  }

  const tidakBisa = sibuk || jalan || (data?.menunggu_prediksi ?? 0) > 0 || !data?.jumlah_teks;

  return (
    <div className="dua">
      <aside aria-label="Pilih media">
        <ul className="pilih-media">
          {media.map((m) => (
            <li key={m.media}>
              <button className={m.media === terpilih ? "aktif" : ""} aria-pressed={m.media === terpilih}
                onClick={() => setTerpilih(m.media)}>
                <span>{m.media}</span>
                <small>
                  {aktif(m.interpretasi.status) ? "Diproses"
                    : m.interpretasi.status === "failed" ? "Gagal"
                    : m.interpretasi.ada_hasil ? (m.interpretasi.basi ? "Belum diperbarui" : "Selesai") : "Belum ada"}
                </small>
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <section className="detail">
        <header className="detail-kepala">
          <div>
            <h1>{terpilih}</h1>
            <p className="redup">{info?.total ?? 0} teks berlabel</p>
          </div>
          <div className="aksi">
            {gagal ? (
              <button disabled={tidakBisa} onClick={() => mulai(() => api.ulangiRun(run.id))}>
                {sibuk ? "Mengirim…" : "Ulangi dari tahap yang gagal"}
              </button>
            ) : (
              <button disabled={tidakBisa} onClick={() => mulai(() => api.jalankan(terpilih))}>
                {jalan ? "Sedang diproses…" : sibuk ? "Mengirim…" : sebelumnya ? "Perbarui interpretasi" : "Jalankan interpretasi"}
              </button>
            )}
          </div>
        </header>

        <Pesan jenis="galat">{galat}</Pesan>
        {data?.menunggu_prediksi > 0 && <Pesan>Prediksi sentimen untuk {data.menunggu_prediksi} teks masih berjalan. Interpretasi bisa dimulai setelah selesai.</Pesan>}
        {info?.interpretasi.basi && !jalan && <Pesan>Ada data baru sejak interpretasi terakhir. Perbarui agar hasil sesuai data terbaru.</Pesan>}
        {jalan && <Pesan>Proses berjalan di layanan AI dan tersimpan di basis data. Halaman ini boleh ditutup; hasil tetap ada saat dibuka lagi. Panggilan pertama bisa lama karena model dimuat dulu.</Pesan>}
        {gagal && <Pesan jenis="galat">{run.error}</Pesan>}

        {!data && !galat && <p className="redup">Memuat…</p>}
        {data && !run && <p className="redup">Interpretasi belum pernah dijalankan untuk media ini.</p>}

        {run && (jalan || gagal || selesaiTerbaru) && (
          <div className="blok">
            <div className="ai-kepala">
              <span className="chip ai">Dihasilkan AI</span>
              <span className="redup">{selesaiTerbaru ? `Selesai ${tanggal(run.finished_at)}` : `Dimulai ${tanggal(run.created_at)}`}</span>
            </div>
            <Tahap run={run} />
            {selesaiTerbaru && run.catatan && <p className="catatan-kecil">{run.catatan}</p>}
          </div>
        )}

        {sebelumnya && !selesaiTerbaru && (
          <details className="blok">
            <summary>Hasil sebelumnya ({tanggal(sebelumnya.finished_at)})</summary>
            <div className="ai-kepala"><span className="chip ai">Dihasilkan AI</span></div>
            <Tahap run={sebelumnya} />
            {sebelumnya.catatan && <p className="catatan-kecil">{sebelumnya.catatan}</p>}
          </details>
        )}
      </section>
    </div>
  );
}
