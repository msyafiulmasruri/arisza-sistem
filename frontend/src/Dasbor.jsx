import { useEffect, useState } from "react";
import AwanKata from "./AwanKata.jsx";
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

function PanelKata({ media }) {
  const [data, setData] = useState(null);
  const [galat, setGalat] = useState("");

  useEffect(() => {
    let batal = false;
    setData(null);
    setGalat("");
    api.kata(media).then((d) => !batal && setData(d)).catch((e) => !batal && setGalat(e.message));
    return () => { batal = true; };
  }, [media]);

  // Canvas digambar ulang bila lebar jendela berubah banyak.
  const [lebar, setLebar] = useState(Math.round(window.innerWidth / 150));
  useEffect(() => {
    let t;
    const ubah = () => { clearTimeout(t); t = setTimeout(() => setLebar(Math.round(window.innerWidth / 150)), 400); };
    window.addEventListener("resize", ubah);
    return () => { window.removeEventListener("resize", ubah); clearTimeout(t); };
  }, []);

  return (
    <section className="blok">
      <h2>Word cloud {media}</h2>
      <p className="redup">Dari teks hasil preprocessing. Semakin besar kata, semakin sering muncul pada sentimen itu.</p>
      <Pesan jenis="galat">{galat}</Pesan>
      {data?.belum_bersih > 0 && (
        <Pesan>{data.belum_bersih} teks belum punya hasil preprocessing, jadi belum masuk word cloud. Lengkapi lewat menu Tabel data.</Pesan>
      )}
      {!data && !galat && <p className="redup">Memuat…</p>}
      {data && (
        <div className="tiga">
          {URUTAN.map((l) => (
            <div key={`${media}-${l}-${lebar}`} className={`kolom-awan ${l}`}>
              <h3>{NAMA[l]}</h3>
              <AwanKata data={data[l]} sentimen={l} />
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default function Dasbor({ media, terpilih, setTerpilih, bukaInterpretasi, bukaImpor }) {
  if (!media) return <p className="redup">Memuat…</p>;
  if (!media.length) return <Kosong bukaImpor={bukaImpor} />;

  const jumlah = media.reduce(
    (a, m) => ({ total: a.total + m.total, positive: a.positive + m.positive, neutral: a.neutral + m.neutral, negative: a.negative + m.negative }),
    { total: 0, positive: 0, neutral: 0, negative: 0 }
  );
  const menunggu = media.reduce((a, m) => a + m.pending, 0);

  return (
    <>
      <section className="ringkas">
        <div>
          <h1>{jumlah.total.toLocaleString("id-ID")} tanggapan dianalisis</h1>
          <p className="redup">dari {media.length} media digital</p>
          <Pesan>{menunggu ? `${menunggu} teks sedang diprediksi.` : ""}</Pesan>
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
              {m.total < 50 && m.total > 0 && <p className="catatan-kecil">Hanya {m.total} teks, jadi hasilnya gambaran awal.</p>}
            </li>
          ))}
        </ul>
      </section>

      {terpilih && <PanelKata media={terpilih} />}
    </>
  );
}
