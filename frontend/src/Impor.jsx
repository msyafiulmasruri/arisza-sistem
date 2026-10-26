import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import { Pesan, STATUS, aktif, tanggal, useBerkala } from "./util.jsx";

export default function Impor({ muatUlang }) {
  const [berkas, setBerkas] = useState(null);
  const [media, setMedia] = useState("");
  const [sibuk, setSibuk] = useState(false);
  const [galat, setGalat] = useState("");
  const [batch, setBatch] = useState([]);
  const input = useRef(null);

  const muat = useCallback(async () => {
    try {
      setBatch(await api.batch());
    } catch (e) {
      setGalat(e.message);
    }
  }, []);

  useEffect(() => { muat(); }, [muat]);
  useBerkala(async () => { await muat(); muatUlang(); }, batch.some((b) => aktif(b.status)), 4000);

  async function kirim(e) {
    e.preventDefault();
    if (!berkas) return;
    setSibuk(true);
    setGalat("");
    try {
      await api.impor(berkas, media);
      setBerkas(null);
      setMedia("");
      if (input.current) input.current.value = "";
      await muat();
      muatUlang();
    } catch (err) {
      setGalat(err.message);
    } finally {
      setSibuk(false);
    }
  }

  async function ulangi(id) {
    setGalat("");
    try {
      await api.ulangiBatch(id);
      await muat();
    } catch (err) {
      setGalat(err.message);
    }
  }

  return (
    <>
      <section className="blok">
        <h1>Impor tanggapan baru</h1>
        <p className="redup">
          Berkas CSV atau Excel (.xlsx) dengan kolom <b>teks</b> (atau komentar, ulasan, tanggapan) dan kolom <b>media</b> (atau platform, sumber).
          Bila berkas tidak punya kolom media, isi nama media di bawah. Maksimal 5.000 baris dan sekitar 4 MB per berkas.
        </p>
        <form className="impor" onSubmit={kirim}>
          <label htmlFor="berkas">Berkas</label>
          <input id="berkas" ref={input} type="file" accept=".csv,.xlsx" onChange={(e) => setBerkas(e.target.files[0] || null)} />
          <label htmlFor="media">Nama media (bila tidak ada kolom media)</label>
          <input id="media" value={media} onChange={(e) => setMedia(e.target.value)} placeholder="Contoh: Instagram" maxLength={100} />
          <button disabled={!berkas || sibuk}>{sibuk ? "Mengunggah…" : "Unggah dan prediksi sentimen"}</button>
        </form>
        <Pesan jenis="galat">{galat}</Pesan>
      </section>

      <section className="blok">
        <h2>Impor terakhir</h2>
        {!batch.length ? (
          <p className="redup">Belum ada impor.</p>
        ) : (
          <ul className="batch">
            {batch.map((b) => (
              <li key={b.id}>
                <div>
                  <strong>{b.filename}</strong>
                  <span className="redup"> {tanggal(b.created_at)}</span>
                </div>
                <div className="batch-status">
                  <span className={`chip c-${b.status}`}>{STATUS[b.status]}</span>
                  <span>{b.diproses} dari {b.total} teks diprediksi</span>
                  {b.status === "failed" && <button className="kecil" onClick={() => ulangi(b.id)}>Ulangi</button>}
                </div>
                {b.status === "failed" && <Pesan jenis="galat">{b.error}</Pesan>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
