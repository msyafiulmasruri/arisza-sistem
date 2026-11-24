import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import { Pesan, STATUS, aktif, persen, tanggal, useBerkala } from "./util.jsx";

export default function Impor({ muatUlang }) {
  const [berkas, setBerkas] = useState(null);
  const [media, setMedia] = useState("");
  const [sibuk, setSibuk] = useState(false);
  const [galat, setGalat] = useState("");
  const [batch, setBatch] = useState([]);
  const [seret, setSeret] = useState(false);
  const input = useRef(null);

  const muat = useCallback(async () => {
    try {
      setBatch(await api.batch());
    } catch (e) {
      setGalat(e.message);
    }
  }, []);

  useEffect(() => {
    muat();
  }, [muat]);

  useBerkala(
    async () => {
      await muat();
      muatUlang();
    },
    batch.some((b) => aktif(b.status)),
    4000
  );

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

  function saatDrop(e) {
    e.preventDefault();
    setSeret(false);
    const f = e.dataTransfer?.files?.[0];
    if (f) setBerkas(f);
  }

  const terbaru = batch[0] || null;
  const namaStatusFile = berkas ? berkas.name : terbaru ? terbaru.filename : "Belum ada file";
  const kodeStatus = berkas ? "ready" : terbaru ? terbaru.status : "waiting";
  const labelStatus = berkas ? "Siap diunggah" : terbaru ? STATUS[terbaru.status] : "Menunggu";
  const diproses = berkas ? 0 : terbaru ? Number(terbaru.diproses || 0) : 0;
  const totalTeks = berkas ? 0 : terbaru ? Number(terbaru.total || 0) : 0;
  const persenProses = totalTeks > 0 ? Math.round(persen(diproses, totalTeks)) : 0;

  return (
    <div className="susun-halaman">
      <div className="grid-impor-atas">
        <section className="kartu">
          <h2>Unggah Dataset</h2>
          <form className="form-impor" onSubmit={kirim}>
            <div
              className={seret ? "dropzone aktif" : "dropzone"}
              onDragOver={(e) => {
                e.preventDefault();
                setSeret(true);
              }}
              onDragLeave={() => setSeret(false)}
              onDrop={saatDrop}
            >
              <input
                id="berkas"
                ref={input}
                type="file"
                accept=".csv,.xlsx"
                className="input-file-tersembunyi"
                onChange={(e) => setBerkas(e.target.files[0] || null)}
              />
              <div className="logo-kotak" aria-hidden="true" />
              <p className="petunjuk-drop">{berkas ? berkas.name : "Seret file ke sini"}</p>
              <button type="button" className="tombol-sekunder" onClick={() => input.current?.click()}>
                Pilih File
              </button>
            </div>

            <p className="keterangan-format">Format .csv / .xlsx</p>

            <div className="baris-aksi-impor">
              <input
                id="media"
                type="text"
                value={media}
                onChange={(e) => setMedia(e.target.value)}
                placeholder="Nama media (opsional)"
                aria-label="Nama media (opsional)"
                maxLength={100}
              />
              <button type="submit" className="tombol-utama" disabled={!berkas || sibuk}>
                {sibuk ? "Mengunggah…" : "Unggah"}
              </button>
            </div>
            <Pesan jenis="galat">{galat}</Pesan>
          </form>
        </section>

        <section className="kartu kartu-status-file">
          <h2>Status File</h2>
          <div className="blok-status-file">
            <span className="redup">Nama file</span>
            <strong className="nama-file-aktif">{namaStatusFile}</strong>
          </div>
          <hr className="pemisah" />
          <div className="baris-status-file">
            <span className="redup">Status</span>
            <span className={`chip c-${kodeStatus}`}>{labelStatus}</span>
          </div>
          <hr className="pemisah" />
          <div className="blok-proses-klasifikasi">
            <div className="baris-status-file">
              <span className="redup">Proses klasifikasi</span>
              <strong>{persenProses}%</strong>
            </div>
            <div className="progress-track" role="progressbar" aria-valuenow={persenProses} aria-valuemin={0} aria-valuemax={100}>
              <div className="progress-fill" style={{ width: `${persenProses}%` }} />
            </div>
            <span className="jumlah-teks-proses">
              {diproses.toLocaleString("id-ID")} dari {totalTeks.toLocaleString("id-ID")} teks
            </span>
          </div>
          <p className="catatan-otomatis">Klasifikasi berjalan otomatis</p>
        </section>
      </div>

      <section className="kartu">
        <h2>Riwayat Unggah</h2>
        {!batch.length ? (
          <p className="redup">Belum ada impor.</p>
        ) : (
          <div className="gulung">
            <table className="tabel-data">
              <thead>
                <tr>
                  <th scope="col">Nama File</th>
                  <th scope="col">Tanggal</th>
                  <th scope="col">Progres</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {batch.map((b) => (
                  <tr key={b.id}>
                    <td>
                      <strong>{b.filename}</strong>
                      {b.status === "failed" && b.error && <div className="teks-galat-kecil">{b.error}</div>}
                    </td>
                    <td className="redup">{tanggal(b.created_at)}</td>
                    <td>
                      {Number(b.diproses || 0).toLocaleString("id-ID")} / {Number(b.total || 0).toLocaleString("id-ID")}
                    </td>
                    <td>
                      <div className="aksi-status-batch">
                        <span className={`chip c-${b.status}`}>{STATUS[b.status]}</span>
                        {b.status === "failed" && (
                          <button className="tombol-sekunder kecil" onClick={() => ulangi(b.id)}>
                            Ulangi
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
