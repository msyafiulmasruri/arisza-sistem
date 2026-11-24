import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import { NAMA, Pesan } from "./util.jsx";

const SEMUA = "";

function useTunda(nilai, ms = 400) {
  const [t, setT] = useState(nilai);
  useEffect(() => {
    const id = setTimeout(() => setT(nilai), ms);
    return () => clearTimeout(id);
  }, [nilai, ms]);
  return t;
}

export default function Tabel({ media, terpilih, bukaImpor }) {
  const [pilihMedia, setPilihMedia] = useState(SEMUA);
  const [label, setLabel] = useState("");
  const [cari, setCari] = useState("");
  const [halaman, setHalaman] = useState(1);
  const [perHalaman] = useState(10);
  const [data, setData] = useState(null);
  const [galat, setGalat] = useState("");
  const [sibukUnduh, setSibukUnduh] = useState(false);
  const q = useTunda(cari);

  useEffect(() => {
    setHalaman(1);
  }, [pilihMedia, label, q, perHalaman]);

  const muat = useCallback(async () => {
    try {
      setData(await api.tabel({ media: pilihMedia, label, q, halaman, per_halaman: perHalaman }));
      setGalat("");
    } catch (e) {
      setGalat(e.message);
    }
  }, [pilihMedia, label, q, halaman, perHalaman]);

  useEffect(() => {
    muat();
  }, [muat]);

  async function unduh() {
    setSibukUnduh(true);
    try {
      await api.unduhCsv({ media: pilihMedia, label, q });
    } catch (e) {
      setGalat(e.message);
    } finally {
      setSibukUnduh(false);
    }
  }

  if (!media) return <p className="redup">Memuat…</p>;
  if (!media.length) {
    return (
      <section className="kosong-blok">
        <h2>Belum ada tanggapan</h2>
        <p>Tabel terisi setelah data diimpor.</p>
        <button className="tombol-utama" onClick={bukaImpor}>Impor Data</button>
      </section>
    );
  }

  const jumlahHalaman = data ? Math.max(1, Math.ceil(data.total / data.per_halaman)) : 1;
  const awal = data && data.total ? (data.halaman - 1) * data.per_halaman + 1 : 0;
  const akhir = data ? Math.min(data.total, data.halaman * data.per_halaman) : 0;

  return (
    <div className="susun-halaman">
      <section className="kartu baris-saring" aria-label="Pencarian dan filter">
        <input
          id="t-cari"
          className="input-cari"
          type="text"
          value={cari}
          onChange={(e) => setCari(e.target.value)}
          placeholder="Cari tanggapan..."
          aria-label="Cari tanggapan"
          maxLength={100}
        />
        <select
          id="t-media"
          value={pilihMedia}
          onChange={(e) => setPilihMedia(e.target.value)}
          aria-label="Filter media digital"
        >
          <option value={SEMUA}>Semua media</option>
          {media.map((m) => (
            <option key={m.media} value={m.media}>
              {m.media} ({m.total.toLocaleString("id-ID")})
            </option>
          ))}
        </select>
        <select
          id="t-label"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          aria-label="Filter sentimen"
        >
          <option value="">Semua sentimen</option>
          {Object.entries(NAMA).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
          <option value="empty">Kosong setelah preprocessing</option>
        </select>
        <button className="tombol-utama tombol-unduh" onClick={unduh} disabled={sibukUnduh || !data?.total}>
          {sibukUnduh ? "Menyiapkan…" : "Unduh Hasil"}
        </button>
      </section>

      <Pesan jenis="galat">{galat}</Pesan>

      <section className="kartu">
        {!data && !galat && <p className="redup">Memuat…</p>}
        {data && (
          <>
            <div className="gulung">
              <table className="tabel-data">
                <thead>
                  <tr>
                    <th scope="col" className="kol-no">No</th>
                    <th scope="col" className="kol-media">Media Digital</th>
                    <th scope="col">Isi Tanggapan</th>
                    <th scope="col" className="kol-sentimen">Sentimen</th>
                  </tr>
                </thead>
                <tbody>
                  {data.baris.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="redup">
                        Tidak ada baris yang cocok.
                      </td>
                    </tr>
                  ) : (
                    data.baris.map((b, i) => (
                      <tr key={b.id}>
                        <td className="redup">{awal + i}</td>
                        <td>{b.media}</td>
                        <td className="teks" title={b.clean_text ? `Hasil preprocessing: ${b.clean_text}` : undefined}>
                          {b.text}
                        </td>
                        <td>
                          {b.label ? (
                            <span
                              className={`chip s-${b.label}`}
                              title={b.confidence != null ? `Confidence: ${b.confidence.toFixed(4)}` : undefined}
                            >
                              {NAMA[b.label]}
                            </span>
                          ) : b.status === "empty" ? (
                            <span className="chip">Kosong</span>
                          ) : (
                            <span className="redup">{b.status === "pending" ? "Menunggu" : "—"}</span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="kaki-tabel">
              <span className="redup" aria-live="polite">
                {data.total
                  ? `${awal.toLocaleString("id-ID")}–${akhir.toLocaleString("id-ID")} dari ${data.total.toLocaleString("id-ID")}`
                  : "0 dari 0"}
              </span>
              <nav className="halaman" aria-label="Halaman tabel">
                <button
                  className="tombol-sekunder kecil"
                  onClick={() => setHalaman((h) => Math.max(1, h - 1))}
                  disabled={halaman <= 1}
                >
                  Sebelumnya
                </button>
                <span className="kotak-halaman" aria-current="page">
                  {halaman}
                </span>
                <button
                  className="tombol-sekunder kecil"
                  onClick={() => setHalaman((h) => Math.min(jumlahHalaman, h + 1))}
                  disabled={halaman >= jumlahHalaman}
                >
                  Berikutnya
                </button>
              </nav>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
