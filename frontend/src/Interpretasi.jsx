import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import { NAMA, Pesan, URUTAN, aktif, tanggal, useBerkala } from "./util.jsx";

function SkeletonBaris({ jumlah = 5 }) {
  return (
    <div className="skeleton-grup" aria-hidden="true">
      {Array.from({ length: jumlah }).map((_, idx) => (
        <span key={idx} className={`skeleton-baris s-${(idx % 5) + 1}`} />
      ))}
    </div>
  );
}

function pecahSaran(teks) {
  if (!teks) return [];
  const baris = String(teks)
    .split(/\n+/)
    .map((b) => b.trim())
    .filter(Boolean);
  const poin = baris.map((b) => b.replace(/^\s*[1-9][.)]\s*/, "").trim()).filter(Boolean);
  return poin.length ? poin : [String(teks).trim()];
}

function PanelPolaDanSaran({ run, info }) {
  const per = Object.fromEntries((run?.tahap || []).map((t) => [t.stage, t]));
  const saranTahap = per.saran;
  const daftarSaran = saranTahap?.status === "done" ? pecahSaran(saranTahap.result) : [];

  return (
    <>
      <section className="kartu">
        <h2>Pola Opini</h2>
        <div className="tiga-kolom">
          {URUTAN.map((id) => {
            const t = per[id];
            const jml = t?.texts_total ?? info?.[id] ?? 0;
            return (
              <article key={id} className="kotak-pola">
                <header className="kepala-pola">
                  <h3>{NAMA[id]}</h3>
                  <span className="redup">{Number(jml).toLocaleString("id-ID")} teks</span>
                </header>
                <div className="isi-pola">
                  {t?.status === "done" && <p className="hasil">{t.result}</p>}
                  {t?.status === "running" && (
                    <>
                      <SkeletonBaris jumlah={5} />
                      <p className="catatan-kecil">Llama sedang menyusun pola opini…</p>
                    </>
                  )}
                  {t?.status === "waiting" && (
                    <>
                      <SkeletonBaris jumlah={5} />
                      <p className="catatan-kecil">Menunggu giliran pemrosesan…</p>
                    </>
                  )}
                  {t?.status === "failed" && <Pesan jenis="galat">{t.error}</Pesan>}
                  {!t && (
                    <>
                      <SkeletonBaris jumlah={5} />
                      <p className="catatan-kecil">Belum ada hasil interpretasi.</p>
                    </>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="kartu">
        <h2>Saran Tindak Lanjut</h2>
        {saranTahap?.status === "failed" && <Pesan jenis="galat">{saranTahap.error}</Pesan>}
        {saranTahap?.status === "done" && daftarSaran.length > 0 ? (
          <ol className="daftar-saran">
            {daftarSaran.map((isi, idx) => (
              <li key={idx} className="item-saran">
                <span className="nomor-saran">{idx + 1}</span>
                <p className="teks-saran">{isi}</p>
              </li>
            ))}
          </ol>
        ) : (
          <ol className="daftar-saran" aria-label="Placeholder saran tindak lanjut">
            {[1, 2, 3].map((no) => (
              <li key={no} className="item-saran">
                <span className="nomor-saran">{no}</span>
                <div className="wadah-skeleton-saran">
                  <span className="skeleton-baris s-1" />
                  <span className="skeleton-baris s-3" />
                  {saranTahap?.status === "running" && no === 1 && (
                    <span className="catatan-kecil">Llama sedang menyusun saran tindak lanjut…</span>
                  )}
                </div>
              </li>
            ))}
          </ol>
        )}
        {run?.status === "done" && run.catatan && <p className="catatan-kecil catatan-bawah">{run.catatan}</p>}
      </section>
    </>
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

  useEffect(() => {
    setData(null);
    muat();
  }, [muat]);

  const run = data?.terbaru;
  const jalan = !!run && aktif(run.status);
  useBerkala(
    async () => {
      await muat();
      muatUlang();
    },
    jalan,
    5000
  );

  if (!media) return <p className="redup">Memuat…</p>;
  if (!media.length) {
    return (
      <section className="kosong-blok">
        <h2>Belum ada media</h2>
        <p>Interpretasi disusun per media setelah data diimpor.</p>
        <button className="tombol-utama" onClick={bukaImpor}>Impor Data</button>
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

  const statusKode = jalan
    ? "running"
    : gagal
      ? "failed"
      : info?.interpretasi.ada_hasil
        ? "done"
        : "waiting";

  const statusLabel = jalan
    ? "Diproses"
    : gagal
      ? "Gagal"
      : info?.interpretasi.ada_hasil
        ? info.interpretasi.basi
          ? "Perlu diperbarui"
          : "Selesai"
        : "Belum ada";

  const runAktif = run || sebelumnya;

  return (
    <div className="susun-halaman">
      <section className="kartu baris-kontrol-interpretasi">
        <div className="kiri-kontrol-interpretasi">
          <select
            id="pilih-media-int"
            value={terpilih}
            onChange={(e) => setTerpilih(e.target.value)}
            aria-label="Pilih media digital"
          >
            {media.map((m) => (
              <option key={m.media} value={m.media}>
                {m.media} ({m.total.toLocaleString("id-ID")} teks)
              </option>
            ))}
          </select>
          <span className="redup">Status:</span>
          <span className={`chip c-${statusKode}`}>{statusLabel}</span>
          {selesaiTerbaru && run?.finished_at && (
            <span className="redup catatan-waktu">{tanggal(run.finished_at)}</span>
          )}
        </div>

        <div className="aksi">
          {gagal ? (
            <button className="tombol-utama" disabled={tidakBisa} onClick={() => mulai(() => api.ulangiInterpretasi(run.id))}>
              {sibuk ? "Mengirim…" : "Ulangi Interpretasi"}
            </button>
          ) : (
            <button className="tombol-utama" disabled={tidakBisa} onClick={() => mulai(() => api.jalankan(terpilih))}>
              {jalan ? "Sedang diproses…" : sibuk ? "Mengirim…" : "Jalankan Interpretasi"}
            </button>
          )}
        </div>
      </section>

      <Pesan jenis="galat">{galat}</Pesan>
      {data?.menunggu_prediksi > 0 && (
        <Pesan>
          Prediksi sentimen untuk {data.menunggu_prediksi} teks masih berjalan. Interpretasi bisa dimulai setelah selesai.
        </Pesan>
      )}
      {info?.interpretasi.basi && !jalan && (
        <Pesan>
          Terdapat data tanggapan baru sejak interpretasi terakhir. Jalankan ulang agar hasil diperbarui.
        </Pesan>
      )}
      {gagal && <Pesan jenis="galat">{run.error}</Pesan>}

      <PanelPolaDanSaran run={runAktif} info={info} />
    </div>
  );
}
