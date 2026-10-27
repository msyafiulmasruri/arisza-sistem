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
  const [perHalaman, setPerHalaman] = useState(25);
  const [data, setData] = useState(null);
  const [galat, setGalat] = useState("");
  const [sibukUnduh, setSibukUnduh] = useState(false);
  const q = useTunda(cari);

  useEffect(() => { setHalaman(1); }, [pilihMedia, label, q, perHalaman]);

  const muat = useCallback(async () => {
    try {
      setData(await api.tabel({ media: pilihMedia, label, q, halaman, per_halaman: perHalaman }));
      setGalat("");
    } catch (e) {
      setGalat(e.message);
    }
  }, [pilihMedia, label, q, halaman, perHalaman]);

  useEffect(() => { muat(); }, [muat]);

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
        <button onClick={bukaImpor}>Impor data</button>
      </section>
    );
  }

  const jumlahHalaman = data ? Math.max(1, Math.ceil(data.total / data.per_halaman)) : 1;
  const awal = data && data.total ? (data.halaman - 1) * data.per_halaman + 1 : 0;
  const akhir = data ? Math.min(data.total, data.halaman * data.per_halaman) : 0;

  return (
    <section className="blok">
      <h1>Tabel data</h1>
      <p className="redup">Setiap baris memuat teks awal, teks hasil preprocessing, sentimen hasil prediksi, skor confidence, dan asal media.</p>

      <div className="saring">
        <div>
          <label htmlFor="t-media">Media</label>
          <select id="t-media" value={pilihMedia} onChange={(e) => setPilihMedia(e.target.value)}>
            <option value={SEMUA}>Semua media</option>
            {media.map((m) => <option key={m.media} value={m.media}>{m.media} ({m.total.toLocaleString("id-ID")})</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="t-label">Sentimen</label>
          <select id="t-label" value={label} onChange={(e) => setLabel(e.target.value)}>
            <option value="">Semua sentimen</option>
            {Object.entries(NAMA).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <div className="lebar">
          <label htmlFor="t-cari">Cari kata</label>
          <input id="t-cari" type="text" value={cari} onChange={(e) => setCari(e.target.value)} placeholder="Cari di teks awal atau hasil preprocessing" maxLength={100} />
        </div>
        <div>
          <label htmlFor="t-per">Baris per halaman</label>
          <select id="t-per" value={perHalaman} onChange={(e) => setPerHalaman(Number(e.target.value))}>
            {[10, 25, 50, 100].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        <div className="aksi-tabel">
          <button className="kecil" onClick={unduh} disabled={sibukUnduh || !data?.total}>{sibukUnduh ? "Menyiapkan…" : "Unduh CSV"}</button>
        </div>
      </div>

      <Pesan jenis="galat">{galat}</Pesan>
      {!data && !galat && <p className="redup">Memuat…</p>}

      {data && (
        <>
          <p className="redup" aria-live="polite">
            {data.total ? `Menampilkan ${awal.toLocaleString("id-ID")}–${akhir.toLocaleString("id-ID")} dari ${data.total.toLocaleString("id-ID")} baris` : "Tidak ada baris yang cocok."}
          </p>
          <div className="gulung">
            <table className="tabel-data">
              <thead>
                <tr>
                  <th scope="col">Media</th>
                  <th scope="col">Teks awal</th>
                  <th scope="col">Teks hasil preprocessing</th>
                  <th scope="col">Sentimen</th>
                  <th scope="col" className="angka">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {data.baris.map((b) => (
                  <tr key={b.id}>
                    <td>{b.media}</td>
                    <td className="teks">{b.text}</td>
                    <td className="teks">{b.clean_text ?? <span className="redup">belum tersedia</span>}</td>
                    <td>
                      {b.label ? <span className={`chip s-${b.label}`}>{NAMA[b.label]}</span>
                        : <span className="redup">{b.status === "pending" ? "menunggu" : "—"}</span>}
                    </td>
                    <td className="angka">{b.confidence == null ? "—" : b.confidence.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <nav className="halaman" aria-label="Halaman tabel">
            <button className="kecil" onClick={() => setHalaman((h) => Math.max(1, h - 1))} disabled={halaman <= 1}>Sebelumnya</button>
            <span>Halaman {halaman} dari {jumlahHalaman}</span>
            <button className="kecil" onClick={() => setHalaman((h) => Math.min(jumlahHalaman, h + 1))} disabled={halaman >= jumlahHalaman}>Berikutnya</button>
          </nav>
        </>
      )}
    </section>
  );
}
