import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import { NAMA, Pesan } from "./util.jsx";

const PILIHAN_LABEL = [
  ["", "Semua sentimen"],
  ["positive", "Positif"],
  ["neutral", "Netral"],
  ["negative", "Negatif"],
  ["empty", "Kosong setelah preprocessing"],
];

const angka = (c) =>
  c == null ? "-" : Number(c).toLocaleString("id-ID", { minimumFractionDigits: 4, maximumFractionDigits: 4 });

export default function Tabel({ media, terpilih }) {
  const [pilihMedia, setPilihMedia] = useState(terpilih || "");
  const [label, setLabel] = useState("");
  const [perHalaman, setPerHalaman] = useState(25);
  const [halaman, setHalaman] = useState(1);
  const [data, setData] = useState(null);
  const [galat, setGalat] = useState("");
  const [info, setInfo] = useState("");

  const muat = useCallback(async () => {
    try {
      setData(await api.tabel({ media: pilihMedia, label, page: halaman, perPage: perHalaman }));
      setGalat("");
    } catch (e) {
      setGalat(e.message);
    }
  }, [pilihMedia, label, halaman, perHalaman]);

  useEffect(() => { muat(); }, [muat]);
  useEffect(() => { setHalaman(1); }, [pilihMedia, label, perHalaman]);

  async function lengkapi() {
    setInfo("");
    try {
      await api.lengkapiPreprocess();
      setInfo("Permintaan dikirim ke layanan AI. Muat ulang beberapa saat lagi.");
    } catch (e) {
      setGalat(e.message);
    }
  }

  const totalHalaman = data ? Math.max(1, Math.ceil(data.total / data.per_page)) : 1;
  const awal = data && data.total ? (data.page - 1) * data.per_page + 1 : 0;

  return (
    <section className="blok">
      <h1>Tabel data</h1>
      <p className="redup">Teks awal, hasil preprocessing, prediksi sentimen, dan skor confidence untuk setiap tanggapan.</p>

      <div className="saring">
        <div>
          <label htmlFor="t-media">Media</label>
          <select id="t-media" value={pilihMedia} onChange={(e) => setPilihMedia(e.target.value)}>
            <option value="">Semua media</option>
            {(media || []).map((m) => <option key={m.media} value={m.media}>{m.media}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="t-label">Sentimen</label>
          <select id="t-label" value={label} onChange={(e) => setLabel(e.target.value)}>
            {PILIHAN_LABEL.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="t-per">Baris per halaman</label>
          <select id="t-per" value={perHalaman} onChange={(e) => setPerHalaman(Number(e.target.value))}>
            {[25, 50, 100].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        <button className="kecil" onClick={muat}>Muat ulang</button>
      </div>

      <Pesan jenis="galat">{galat}</Pesan>
      {data?.belum_bersih > 0 && (
        <Pesan>
          {data.belum_bersih} teks belum punya hasil preprocessing (data diimpor sebelum fitur ini ada).{" "}
          <button className="kecil" onClick={lengkapi}>Lengkapi preprocessing</button>
        </Pesan>
      )}
      <Pesan>{info}</Pesan>

      {!data && !galat && <p className="redup">Memuat…</p>}
      {data && (
        <>
          <p className="redup" aria-live="polite">
            {data.total ? `Menampilkan ${awal}-${awal + data.rows.length - 1} dari ${data.total.toLocaleString("id-ID")} baris` : "Tidak ada baris yang cocok."}
          </p>
          <div className="gulung">
            <table className="tabel-data">
              <thead>
                <tr>
                  <th>No</th>
                  <th>Media</th>
                  <th>Teks awal</th>
                  <th>Hasil preprocessing</th>
                  <th>Prediksi sentimen</th>
                  <th className="angka">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((r, i) => (
                  <tr key={r.id}>
                    <td>{awal + i}</td>
                    <td>{r.media}</td>
                    <td className="isi-teks">{r.text}</td>
                    <td className="isi-teks">{r.text_clean ?? <span className="redup">belum diproses</span>}</td>
                    <td>
                      {r.status === "empty"
                        ? <span className="chip">Kosong</span>
                        : <span className={`chip s-${r.label}`}>{NAMA[r.label]}</span>}
                    </td>
                    <td className="angka">{angka(r.confidence)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="halaman">
            <button className="kecil" disabled={data.page <= 1} onClick={() => setHalaman(data.page - 1)}>Sebelumnya</button>
            <span>Halaman {data.page} dari {totalHalaman}</span>
            <button className="kecil" disabled={data.page >= totalHalaman} onClick={() => setHalaman(data.page + 1)}>Berikutnya</button>
          </div>
        </>
      )}
    </section>
  );
}
