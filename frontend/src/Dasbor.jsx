import { useEffect, useState } from "react";
import { api } from "./api.js";
import { BarSentimen, NAMA, Pesan, URUTAN, persen } from "./util.jsx";

function Kosong({ bukaImpor }) {
  return (
    <section className="kosong-blok">
      <h2>Belum ada tanggapan</h2>
      <p>Unggah berkas CSV atau Excel berisi tanggapan pengunjung. Sentimen setiap teks diprediksi otomatis.</p>
      <button className="tombol-utama" onClick={bukaImpor}>Impor Data</button>
    </section>
  );
}

function PlaceholderWordCloud() {
  return (
    <div className="wc-placeholder" aria-hidden="true">
      <span className="wcp b1" />
      <span className="wcp b2" />
      <span className="wcp b3" />
      <span className="wcp b4" />
      <span className="wcp b5" />
      <span className="wcp b6" />
    </div>
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
          if (!ada) {
            hasil[l] = null;
            continue;
          }
          try {
            const url = await api.gambarWordcloud(media, l);
            if (batal) {
              URL.revokeObjectURL(url);
              continue;
            }
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
    return () => {
      batal = true;
      alamat.forEach((u) => URL.revokeObjectURL(u));
    };
  }, [media, versi]);

  return (
    <section className="kartu">
      <div className="kepala-kartu">
        <h2>Word Cloud</h2>
        <span className="redup">{media}</span>
      </div>
      <Pesan jenis="galat">{galat}</Pesan>
      <div className="tiga-kolom">
        {URUTAN.map((l) => (
          <figure key={l} className={`kotak-wc ${l}`}>
            <figcaption className="kepala-wc">
              <h3>{NAMA[l]}</h3>
              {gambar[l] && <span className="redup">{gambar[l].n.toLocaleString("id-ID")} teks</span>}
            </figcaption>
            {!memuat && gambar[l] ? (
              <img
                className="wc"
                src={gambar[l].url}
                alt={`Word Cloud sentimen ${NAMA[l].toLowerCase()} pada ${media}`}
              />
            ) : (
              <div className="wc-kosong">
                <PlaceholderWordCloud />
                <p className="catatan-kecil">
                  {memuat
                    ? "Memuat…"
                    : menunggu
                      ? "Menunggu prediksi sentimen selesai…"
                      : perluLengkap
                        ? "Belum tersedia. Lengkapi data lama dulu."
                        : "Belum ada teks pada sentimen ini."}
                </p>
              </div>
            )}
          </figure>
        ))}
      </div>
    </section>
  );
}

export default function Dasbor({ media, muatUlang, terpilih, setTerpilih, bukaInterpretasi, bukaImpor }) {
  const [sibukLengkap, setSibukLengkap] = useState(false);
  const [pesanLengkap, setPesanLengkap] = useState("");
  const [galatLengkap, setGalatLengkap] = useState("");

  if (!media) return <p className="redup">Memuat…</p>;
  if (!media.length) return <Kosong bukaImpor={bukaImpor} />;

  const jumlah = media.reduce(
    (a, m) => ({
      total: a.total + m.total,
      positive: a.positive + m.positive,
      neutral: a.neutral + m.neutral,
      negative: a.negative + m.negative,
    }),
    { total: 0, positive: 0, neutral: 0, negative: 0 }
  );
  const menunggu = media.reduce((a, m) => a + m.pending, 0);
  const perluLengkap = media.reduce((a, m) => a + (m.perlu_lengkap ?? 0), 0);
  const maksSentimen = Math.max(1, jumlah.positive, jumlah.neutral, jumlah.negative);

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
    <div className="susun-halaman">
      <section className="grid-ringkasan" aria-label="Ringkasan sentimen">
        <div className="kartu-metrik">
          <span className="label-metrik">Total Tanggapan</span>
          <div className="nilai-baris">
            <strong className="nilai-metrik">{jumlah.total.toLocaleString("id-ID")}</strong>
          </div>
        </div>
        {URUTAN.map((l) => (
          <div key={l} className="kartu-metrik">
            <span className="label-metrik">{NAMA[l]}</span>
            <div className="nilai-baris">
              <strong className="nilai-metrik">{jumlah[l].toLocaleString("id-ID")}</strong>
              <span className="persen-metrik">{persen(jumlah[l], jumlah.total)}%</span>
            </div>
          </div>
        ))}
      </section>

      {menunggu > 0 && <Pesan>{menunggu.toLocaleString("id-ID")} teks sedang diprediksi.</Pesan>}
      {perluLengkap > 0 && (
        <div className="pesan">
          {perluLengkap.toLocaleString("id-ID")} teks lama belum punya hasil preprocessing dan Word Cloud.{" "}
          <button className="tombol-sekunder kecil" onClick={lengkapi} disabled={sibukLengkap}>
            {sibukLengkap ? "Mengirim…" : "Lengkapi data lama"}
          </button>
        </div>
      )}
      <Pesan>{pesanLengkap}</Pesan>
      <Pesan jenis="galat">{galatLengkap}</Pesan>

      <div className="grid-tengah-dasbor">
        <section className="kartu">
          <h2>Distribusi Sentimen</h2>
          <div
            className="grafik-batang"
            role="img"
            aria-label={URUTAN.map((l) => `${NAMA[l]} ${jumlah[l]} (${persen(jumlah[l], jumlah.total)}%)`).join(", ")}
          >
            <div className="area-batang">
              {URUTAN.map((l) => {
                const tinggi = jumlah[l] ? Math.max(8, Math.round((jumlah[l] / maksSentimen) * 100)) : 2;
                return (
                  <div key={l} className="kolom-batang">
                    <div className="wadah-batang">
                      <div
                        className={`batang ${l}`}
                        style={{ height: `${tinggi}%` }}
                        title={`${NAMA[l]}: ${jumlah[l].toLocaleString("id-ID")} (${persen(jumlah[l], jumlah.total)}%)`}
                      />
                    </div>
                    <span className="label-batang">{NAMA[l]}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        <section className="kartu">
          <h2>Hasil per Media Digital</h2>
          <ul className="daftar-media">
            {media.map((m) => (
              <li key={m.media} className={m.media === terpilih ? "dipilih" : ""}>
                <div className="baris-media">
                  <button
                    className="nama-media"
                    onClick={() => setTerpilih(m.media)}
                    aria-pressed={m.media === terpilih}
                  >
                    {m.media}
                  </button>
                  <span className="redup">{m.total.toLocaleString("id-ID")} teks</span>
                  <span className="grup-bar">
                    <BarSentimen data={m} />
                  </span>
                  <button className="tombol-sekunder kecil" onClick={() => bukaInterpretasi(m.media)}>
                    Interpretasi
                  </button>
                </div>
                {m.total < 50 && m.total > 0 && (
                  <p className="catatan-kecil">Hanya {m.total} teks, jadi pola yang terlihat belum tentu mewakili.</p>
                )}
              </li>
            ))}
          </ul>
        </section>
      </div>

      {terpilih && dipilih && (
        <PanelWordCloud
          media={terpilih}
          versi={`${dipilih.total}:${dipilih.pending}:${dipilih.perlu_lengkap ?? 0}`}
          perluLengkap={(dipilih.perlu_lengkap ?? 0) > 0}
          menunggu={(dipilih.pending ?? 0) > 0}
        />
      )}
    </div>
  );
}
