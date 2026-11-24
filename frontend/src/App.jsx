import { useCallback, useEffect, useState } from "react";
import { api, adaToken, hapusToken, simpanToken } from "./api.js";
import { Pesan, aktif, useBerkala } from "./util.jsx";
import Dasbor from "./Dasbor.jsx";
import Interpretasi from "./Interpretasi.jsx";
import Impor from "./Impor.jsx";
import Tabel from "./Tabel.jsx";

function Masuk({ onMasuk }) {
  const [email, setEmail] = useState("");
  const [sandi, setSandi] = useState("");
  const [galat, setGalat] = useState("");
  const [sibuk, setSibuk] = useState(false);

  async function kirim(e) {
    e.preventDefault();
    setSibuk(true);
    setGalat("");
    try {
      const hasil = await api.masuk(email, sandi);
      simpanToken(hasil.access_token);
      onMasuk(hasil.user?.email || email);
    } catch (err) {
      setGalat(err.message);
    } finally {
      setSibuk(false);
    }
  }

  return (
    <main className="masuk-halaman">
      <section className="kartu-login">
        <div className="identitas-login">
          <div className="logo-kotak besar" aria-hidden="true" />
          <h1>Arisza Library &amp; Learning</h1>
        </div>
        <hr className="pemisah" />
        <h2 className="judul-login">Login</h2>
        <form onSubmit={kirim}>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            placeholder="nama@email.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
            maxLength={254}
            required
          />
          <label htmlFor="sandi">Password</label>
          <input
            id="sandi"
            type="password"
            placeholder="••••••••"
            value={sandi}
            onChange={(e) => setSandi(e.target.value)}
            autoComplete="current-password"
            required
          />
          <button className="tombol-utama penuh" disabled={sibuk || !email.trim() || !sandi}>
            {sibuk ? "Memeriksa…" : "Login"}
          </button>
          <Pesan jenis="galat">{galat}</Pesan>
        </form>
      </section>
    </main>
  );
}

const MENU = [
  ["dasbor", "Dashboard"],
  ["impor", "Impor Data"],
  ["tabel", "Data Tanggapan"],
  ["interpretasi", "Interpretasi"],
];

const JUDUL = Object.fromEntries(MENU);

export default function App() {
  const [masuk, setMasuk] = useState(adaToken());
  const [tab, setTab] = useState("dasbor");
  const [media, setMedia] = useState(null);
  const [galat, setGalat] = useState("");
  const [terpilih, setTerpilih] = useState("");
  const [emailPengguna, setEmailPengguna] = useState("");

  const muat = useCallback(async () => {
    try {
      const data = await api.ringkasan();
      setMedia(data);
      setGalat("");
      setTerpilih((s) => s || data[0]?.media || "");
    } catch (err) {
      if (err.status === 401) {
        hapusToken();
        setMasuk(false);
      } else {
        setGalat(err.message);
      }
    }
  }, []);

  useEffect(() => {
    if (!masuk) return;
    muat();
    api.penggunaAktif().then((u) => setEmailPengguna(u?.email || "")).catch(() => {});
  }, [masuk, muat]);

  const adaProses = !!media?.some((m) => aktif(m.interpretasi.status) || m.pending > 0);
  useBerkala(muat, masuk && adaProses, 6000);

  if (!masuk) {
    return (
      <Masuk
        onMasuk={(em) => {
          if (em) setEmailPengguna(em);
          setMasuk(true);
        }}
      />
    );
  }

  return (
    <div className="aplikasi">
      <aside className="sidebar">
        <div className="identitas-sidebar">
          <div className="logo-kotak" aria-hidden="true" />
          <div className="teks-identitas">
            <strong>Arisza Library</strong>
            <span>&amp; Learning</span>
          </div>
        </div>
        <nav className="menu-sidebar" aria-label="Menu utama">
          {MENU.map(([id, label]) => (
            <button
              key={id}
              className={tab === id ? "item-menu aktif" : "item-menu"}
              aria-current={tab === id ? "page" : undefined}
              onClick={() => setTab(id)}
            >
              <span className="ikon-menu" aria-hidden="true" />
              <span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-bawah">
          <button
            className="tombol-sekunder penuh"
            onClick={() => {
              hapusToken();
              setMasuk(false);
              setMedia(null);
              setEmailPengguna("");
            }}
          >
            Logout
          </button>
        </div>
      </aside>

      <div className="area-utama">
        <header className="topbar">
          <h1 className="judul-topbar">{JUDUL[tab]}</h1>
          <div className="akun-kotak" title={emailPengguna || "Pengelola"}>
            <span className="avatar-kotak" aria-hidden="true" />
            <span>Pengelola</span>
          </div>
        </header>

        <main className="isi">
          <Pesan jenis="galat">{galat}</Pesan>
          {tab === "dasbor" && (
            <Dasbor
              media={media}
              muatUlang={muat}
              terpilih={terpilih}
              setTerpilih={setTerpilih}
              bukaInterpretasi={(m) => {
                setTerpilih(m);
                setTab("interpretasi");
              }}
              bukaImpor={() => setTab("impor")}
            />
          )}
          {tab === "impor" && <Impor muatUlang={muat} />}
          {tab === "tabel" && <Tabel media={media} terpilih={terpilih} bukaImpor={() => setTab("impor")} />}
          {tab === "interpretasi" && (
            <Interpretasi
              media={media}
              terpilih={terpilih}
              setTerpilih={setTerpilih}
              muatUlang={muat}
              bukaImpor={() => setTab("impor")}
            />
          )}
        </main>

        <footer className="kaki">
          <p>
            Built with Llama. Llama 3.2 is licensed under the Llama 3.2 Community License, Copyright © Meta Platforms,
            Inc. All Rights Reserved.
          </p>
        </footer>
      </div>
    </div>
  );
}
