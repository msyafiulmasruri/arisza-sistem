import { useCallback, useEffect, useState } from "react";
import { api, adaKunci, hapusKunci, simpanKunci } from "./api.js";
import { Pesan, aktif, useBerkala } from "./util.jsx";
import Dasbor from "./Dasbor.jsx";
import Interpretasi from "./Interpretasi.jsx";
import Impor from "./Impor.jsx";
import Tabel from "./Tabel.jsx";

function Masuk({ onMasuk }) {
  const [sandi, setSandi] = useState("");
  const [galat, setGalat] = useState("");
  const [sibuk, setSibuk] = useState(false);

  async function kirim(e) {
    e.preventDefault();
    setSibuk(true);
    setGalat("");
    try {
      await api.masuk(sandi);
      simpanKunci(sandi);
      onMasuk();
    } catch (err) {
      setGalat(err.message);
    } finally {
      setSibuk(false);
    }
  }

  return (
    <main className="masuk">
      <h1>Arisza Library &amp; Learning</h1>
      <p className="sub">Masuk untuk melihat analisis sentimen tanggapan pengunjung.</p>
      <form onSubmit={kirim}>
        <label htmlFor="sandi">Kata sandi</label>
        <input id="sandi" type="password" value={sandi} onChange={(e) => setSandi(e.target.value)}
          autoComplete="current-password" required />
        <button disabled={sibuk || !sandi}>{sibuk ? "Memeriksa…" : "Masuk"}</button>
        <Pesan jenis="galat">{galat}</Pesan>
      </form>
    </main>
  );
}

const TAB = [
  ["dasbor", "Dasbor"],
  ["tabel", "Tabel data"],
  ["interpretasi", "Interpretasi"],
  ["impor", "Impor data"],
];

export default function App() {
  const [masuk, setMasuk] = useState(adaKunci());
  const [tab, setTab] = useState("dasbor");
  const [media, setMedia] = useState(null); // null = belum dimuat
  const [galat, setGalat] = useState("");
  const [terpilih, setTerpilih] = useState("");

  const muat = useCallback(async () => {
    try {
      const data = await api.ringkasan();
      setMedia(data);
      setGalat("");
      setTerpilih((s) => s || data[0]?.media || "");
    } catch (err) {
      if (err.status === 401) {
        hapusKunci();
        setMasuk(false);
      } else setGalat(err.message);
    }
  }, []);

  useEffect(() => {
    if (masuk) muat();
  }, [masuk, muat]);

  const adaProses = !!media?.some((m) => aktif(m.interpretasi.status) || m.pending > 0);
  useBerkala(muat, masuk && adaProses, 6000);

  if (!masuk) return <Masuk onMasuk={() => setMasuk(true)} />;

  return (
    <>
      <header className="atas">
        <div className="merek">
          <strong>Arisza</strong>
          <span>Analisis sentimen tanggapan pengunjung</span>
        </div>
        <nav aria-label="Menu utama">
          {TAB.map(([id, label]) => (
            <button key={id} className={tab === id ? "tab aktif" : "tab"} aria-current={tab === id ? "page" : undefined}
              onClick={() => setTab(id)}>{label}</button>
          ))}
        </nav>
        <button className="tautan" onClick={() => { hapusKunci(); setMasuk(false); }}>Keluar</button>
      </header>
      <main className="isi">
        <Pesan jenis="galat">{galat}</Pesan>
        {tab === "dasbor" && <Dasbor media={media} muatUlang={muat} terpilih={terpilih} setTerpilih={setTerpilih} bukaInterpretasi={(m) => { setTerpilih(m); setTab("interpretasi"); }} bukaImpor={() => setTab("impor")} />}
        {tab === "tabel" && <Tabel media={media} terpilih={terpilih} bukaImpor={() => setTab("impor")} />}
        {tab === "interpretasi" && <Interpretasi media={media} terpilih={terpilih} setTerpilih={setTerpilih} muatUlang={muat} bukaImpor={() => setTab("impor")} />}
        {tab === "impor" && <Impor muatUlang={muat} />}
      </main>
      <footer className="kaki">
        <p>Built with Llama. Llama 3.2 is licensed under the Llama 3.2 Community License, Copyright © Meta Platforms, Inc. All Rights Reserved.</p>
      </footer>
    </>
  );
}
