import { useEffect, useState } from "react";
import { api } from "./api.js";
import { BarSentimen, NAMA, Pesan, URUTAN, persen, tanggal } from "./util.jsx";

function Kosong({ bukaImpor }) {
  return (
    <section className="kosong-blok">
      <h2>Belum ada tanggapan</h2>
      <p>Unggah berkas CSV atau Excel berisi tanggapan pengunjung. Sentimen setiap teks diprediksi otomatis.</p>
      <button onClick={bukaImpor}>Impor data</button>
    </section>
  );
}

function PanelWordCloud({ media, versi, perluLengkap, menunggu }) {
  const [gambar, setGambar] = useState({});
  const [galat, setGalat] = useState("");
  const [memuat, setMemuat] = useState(true);

  useEffect(() => {
    let batal = false;
    const alamat = [];
    setGambar({});
    setGalat("");
    setMemuat(true);
    (async () => {
      try {
        const daftar = await api.infoWordcloud(media);
        const hasil = {};
        for (const l of URUTAN) {
          const ada = daftar.find((d) => d.label === l);
          if (!ada) { hasil[l] = null; continue; }
          try {
            const url = await api.gambarWordcloud(media, l);
            if (batal) { URL.revokeObjectURL(url); continue; } // efek sudah dibersihkan
            alamat.push(url);
            hasil[l] = { url, n: ada.n_texts };
          } catch {
            hasil[l] = null;
          }
        }
        if (!batal) setGambar(hasil);
      } catch (e) {
        if (!batal) setGalat(e.message);
      } finally {
        if (!batal) setMemuat(false);
      }
    })();
    return () => { batal = true; alamat.forEach((u) => URL.revokeObjectURL(u)); };
  }, [media, versi]);

  return (
    <section className="blok">
      <h2>Word Cloud {media}</h2>
      <p className="redup">Kata yang paling sering muncul pada tiap sentimen, dibuat dari teks hasil preprocessing tanpa stopword.</p>
      <Pesan jenis="galat">{galat}</Pesan>
      {memuat && <p className="redup">Memuat…</p>}
      {!memuat && !galat && (
        <div className="tiga">
          {URUTAN.map((l) => (
            <figure key={l} className={`kolom-awan ${l}`}>
              <figcaption><h3>{NAMA[l]}</h3></figcaption>
              {gambar[l] ? (
                <>
                  <img className="wc" src={gambar[l].url} alt={`Word Cloud sentimen ${NAMA[l].toLowerCase()} pada ${media}`} />
                  <p className="catatan-kecil">{gambar[l].n.toLocaleString("id-ID")} teks</p>
                </>
              ) : (
                <p className="redup">
                  {menunggu
                    ? "Menunggu prediksi sentimen selesai…"
                    : perluLengkap
                      ? "Belum tersedia. Lengkapi data lama dulu."
                      : "Belum ada teks pada sentimen ini."}
                </p>
              )}
            </figure>
          ))}
        </div>
      )}
    </section>
  );
}

export default function Dasbor({ media, muatUlang, terpilih, setTerpilih, bukaInterpretasi, bukaImpor }) {
  // Hook harus dipanggil sebelum return lebih awal; bila tidak, React galat
  // "Rendered more hooks than during the previous render" saat data selesai dimuat.
  const [sibukLengkap, setSibukLengkap] = useState(false);
  const [pesanLengkap, setPesanLengkap] = useState("");
  const [galatLengkap, setGalatLengkap] = useState("");

  if (!media) return <p className="redup">Memuat…</p>;
  if (!media.length) return <Kosong bukaImpor={bukaImpor} />;

  const jumlah = media.reduce(
    (a, m) => ({ total: a.total + m.total, positive: a.positive + m.positive, neutral: a.neutral + m.neutral, negative: a.negative + m.negative }),
    { total: 0, positive: 0, neutral: 0, negative: 0 }
  );
  const menunggu = media.reduce((a, m) => a + m.pending, 0);
  const perluLengkap = media.reduce((a, m) => a + (m.perlu_lengkap ?? 0), 0);

  async function lengkapi() {
    setSibukLengkap(true);
    setGalatLengkap("");
    try {
      await api.lengkapi();
      setPesanLengkap("Permintaan diterima. Layanan AI sedang melengkapi data; muat ulang halaman beberapa saat lagi.");
      setTimeout(muatUlang, 15000);
    } catch (e) {
      setGalatLengkap(e.message);
    } finally {
      setSibukLengkap(false);
    }
  }
  const dipilih = media.find((m) => m.media === terpilih);

  return (
    <>
      <section className="ringkas">
        <div>
          <h1>{jumlah.total.toLocaleString("id-ID")} tanggapan dianalisis</h1>
          <p className="redup">dari {media.length} media digital</p>
          <Pesan>{menunggu ? `${menunggu} teks sedang diprediksi.` : ""}</Pesan>
          {perluLengkap > 0 && (
            <div className="pesan">
              {perluLengkap.toLocaleString("id-ID")} teks lama belum punya hasil preprocessing dan Word Cloud.{" "}
              <button className="kecil" onClick={lengkapi} disabled={sibukLengkap}>{sibukLengkap ? "Mengirim…" : "Lengkapi data lama"}</button>
            </div>
          )}
          <Pesan>{pesanLengkap}</Pesan>
          <Pesan jenis="galat">{galatLengkap}</Pesan>
        </div>
        <div className="besar">
          <BarSentimen data={jumlah} />
          <ul className="legenda">
            {URUTAN.map((l) => (
              <li key={l}><span className={`titik ${l}`} />{NAMA[l]} {jumlah[l].toLocaleString("id-ID")} ({persen(jumlah[l], jumlah.total)}%)</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="blok">
        <h2>Distribusi sentimen per media</h2>
        <ul className="daftar-media">
          {media.map((m) => (
            <li key={m.media} className={m.media === terpilih ? "dipilih" : ""}>
              <div className="baris-media">
                <button className="nama-media" onClick={() => setTerpilih(m.media)} aria-pressed={m.media === terpilih}>
                  {m.media}
                </button>
                <span className="redup">{m.total.toLocaleString("id-ID")} teks</span>
                <span className="grup-bar"><BarSentimen data={m} /></span>
                <span className="status-int">
                  {m.interpretasi.ada_hasil
                    ? m.interpretasi.basi ? "Interpretasi belum diperbarui" : `Interpretasi ${tanggal(m.interpretasi.selesai_pada)}`
                    : "Belum diinterpretasi"}
                </span>
                <button className="kecil" onClick={() => bukaInterpretasi(m.media)}>Lihat interpretasi</button>
              </div>
              {m.total < 50 && m.total > 0 && <p className="catatan-kecil">Hanya {m.total} teks, jadi pola yang terlihat belum tentu mewakili.</p>}
            </li>
          ))}
        </ul>
      </section>

      {terpilih && dipilih && (
        <PanelWordCloud
          media={terpilih}
          versi={`${dipilih.total}:${dipilih.pending}:${dipilih.perlu_lengkap ?? 0}`}
          perluLengkap={(dipilih.perlu_lengkap ?? 0) > 0}
          menunggu={(dipilih.pending ?? 0) > 0}
        />
      )}
    </>
  );
}
