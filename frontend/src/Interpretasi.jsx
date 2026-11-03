import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import { Pesan, STATUS, aktif, lama, tanggal, useBerkala } from "./util.jsx";

const TAHAP = [
  ["positive", "Pola opini positif"],
  ["neutral", "Pola opini netral"],
  ["negative", "Pola opini negatif"],
  ["saran", "Saran tindak lanjut"],
];

function DaftarFrekuensi({ judul, daftar }) {
  if (!daftar?.length) return <p className="catatan-kecil">Tidak ada kata atau frasa yang memenuhi kriteria.</p>;
  return (
    <div className="gulung">
      <h4>{judul}</h4>
      <table className="tabel-data">
        <thead><tr><th>{judul === "Kata yang sering muncul" ? "Kata" : "Frasa"}</th><th className="angka">Kemunculan</th></tr></thead>
        <tbody>
          {daftar.map((item) => (
            <tr key={item.teks}>
              <td>{item.teks}</td>
              <td className="angka">{Number(item.frekuensi || 0).toLocaleString("id-ID")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Tahap({ run }) {
  const per = Object.fromEntries(run.tahap.map((t) => [t.stage, t]));
  return (
    <ol className="tahap">
      {TAHAP.map(([id, judul]) => {
        const t = per[id];
        if (!t) return null;
        return (
          <li key={id} className={`t-${t.status}`}>
            <div className="t-kepala">
              <h3>{judul}</h3>
              <span className="chip">{STATUS[t.status]}</span>
              {t.status === "done" && t.duration > 0 && <span className="redup">{lama(t.duration)}</span>}
              {id !== "saran" && t.status === "done" && t.texts_total > 0 && (
                <span className="redup">{t.texts_total.toLocaleString("id-ID")} tanggapan dianalisis</span>
              )}
            </div>
            {t.status === "running" && (
              <div className="proses">
                <p className="redup">
                  {id === "saran"
                    ? "Llama sedang menyusun saran tindak lanjut…"
                    : "Llama sedang menyusun pola opini berdasarkan frekuensi kata dan frasa…"}
                </p>
              </div>
            )}
            {t.status === "failed" && <Pesan jenis="galat">{t.error}</Pesan>}
            {t.status === "done" && <p className="hasil">{t.result}</p>}
            {t.status === "done" && id !== "saran" && t.detail?.metode === "frekuensi_v1" && (
              <details className="rincian">
                <summary>Lihat kata dan frasa yang dianalisis</summary>
                <p className="catatan-kecil">
                  Penghitungan dilakukan terhadap {(t.detail.jumlah_tanggapan ?? t.texts_total ?? 0).toLocaleString("id-ID")} tanggapan.
                  Angka menunjukkan jumlah kemunculan kata atau frasa, bukan jumlah pengunjung yang berbeda.
                </p>
                <DaftarFrekuensi judul="Kata yang sering muncul" daftar={t.detail.kata} />
                <DaftarFrekuensi judul="Frasa yang sering muncul" daftar={t.detail.frasa} />
                {t.detail.waktu_penghitungan != null && (
                  <p className="catatan-kecil">Waktu penghitungan Python: {durasiRinci(t.detail.waktu_penghitungan)}.</p>
                )}
                {!t.detail.llama_dipanggil && (
                  <p className="catatan-kecil">Llama tidak dipanggil karena tidak tersedia kata atau frasa yang cukup untuk diinterpretasikan.</p>
                )}
              </details>
            )}
          </li>
        );
      })}
    </ol>
  );
}

const totalDurasi = (run) => run.tahap.reduce((a, t) => a + (t.status === "done" ? Number(t.duration || 0) : 0), 0);
const durasiRinci = (detik) => Number(detik) < 1
  ? `${Number(detik).toFixed(2).replace(".", ",")} detik`
  : lama(detik);

function WaktuSemuaMedia({ media }) {
  const baris = media.filter((m) => m.interpretasi.ada_hasil && m.interpretasi.total_detik != null);
  if (!baris.length) return null;
  return (
    <div className="blok">
      <h2>Waktu pemrosesan Llama per media</h2>
      <p className="redup">
        Dari interpretasi terakhir yang selesai pada tiap media. Waktu diukur di Space (CPU) dan tidak termasuk
        pemuatan model.
      </p>
      <div className="gulung">
        <table className="tabel-data">
          <thead><tr><th>Media</th><th className="angka">Jumlah teks</th><th className="angka">Total waktu Llama</th></tr></thead>
          <tbody>
            {baris.map((m) => (
              <tr key={m.media}>
                <td>{m.media}</td>
                <td className="angka">{(m.interpretasi.n_teks ?? m.total ?? 0).toLocaleString("id-ID")}</td>
                <td className="angka">{lama(m.interpretasi.total_detik)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
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
        {info?.interpretasi.basi && !jalan && <Pesan>Interpretasi belum menggunakan metode frekuensi kata dan frasa terbaru atau terdapat data baru. Jalankan ulang agar hasil diperbarui.</Pesan>}
        {jalan && <Pesan>Proses berjalan di layanan AI dan tersimpan di basis data. Python menghitung kata dan frasa yang sering muncul, kemudian Llama menyusun pola opini serta saran tindak lanjut. Halaman ini boleh ditutup; hasil tetap tersedia saat dibuka kembali.</Pesan>}
        {gagal && <Pesan jenis="galat">{run.error}</Pesan>}

        {!data && !galat && <p className="redup">Memuat…</p>}
        {data && !run && <p className="redup">Interpretasi belum pernah dijalankan untuk media ini.</p>}

        {run && (jalan || gagal || selesaiTerbaru) && (
          <div className="blok">
            <div className="ai-kepala">
              <span className="chip ai">Dihasilkan AI</span>
              <span className="redup">{selesaiTerbaru ? `Selesai ${tanggal(run.finished_at)}` : `Dimulai ${tanggal(run.created_at)}`}</span>
              {totalDurasi(run) > 0 && (
                <span className="redup">Total waktu Llama: <b>{lama(totalDurasi(run))}</b></span>
              )}
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

        <WaktuSemuaMedia media={media} />
      </section>
    </div>
  );
}
