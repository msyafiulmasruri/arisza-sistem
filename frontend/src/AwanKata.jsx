import { useEffect, useRef } from "react";
import WordCloud from "wordcloud";

const WARNA = {
  positive: ["#1f5a41", "#2e7d5a", "#3a8f69", "#27694c"],
  neutral: ["#3d4753", "#566273", "#6a7888", "#48535f"],
  negative: ["#7a2d26", "#9c3b32", "#b4463c", "#8c342c"],
};

const sebar = (kata) => [...kata].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7);

/** Word cloud sungguhan (canvas). data: [{kata, jumlah}] terurut dari yang terbanyak. */
export default function AwanKata({ data, sentimen, tinggi = 300 }) {
  const ref = useRef(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas || !data.length) return;
    const lebar = Math.max(200, canvas.parentElement.clientWidth - 8);
    const dpr = window.devicePixelRatio || 1;
    canvas.style.width = `${lebar}px`;
    canvas.style.height = `${tinggi}px`;
    canvas.width = Math.round(lebar * dpr);
    canvas.height = Math.round(tinggi * dpr);
    const maks = data[0].jumlah;
    const min = data[data.length - 1].jumlah;
    WordCloud(canvas, {
      list: data.map((d) => [d.kata, d.jumlah]),
      gridSize: Math.round(5 * dpr),
      weightFactor: (w) => (13 + ((w - min) / Math.max(1, maks - min)) * 36) * dpr,
      fontFamily: "Figtree, system-ui, sans-serif",
      fontWeight: 600,
      color: (kata) => WARNA[sentimen][sebar(kata) % 4],
      backgroundColor: "#ffffff",
      rotateRatio: 0.2,
      minRotation: Math.PI / 2,
      maxRotation: Math.PI / 2,
      shrinkToFit: true,
      drawOutOfBound: false,
    });
  }, [data, sentimen, tinggi]);

  if (!data.length) return <p className="redup">Belum ada kata.</p>;
  const label = data.slice(0, 10).map((d) => d.kata).join(", ");
  return (
    <>
      <canvas ref={ref} role="img" aria-label={`Word cloud, kata terbanyak: ${label}`} className="kanvas-awan" />
      <details className="daftar-kata">
        <summary>Daftar kata dan jumlahnya</summary>
        <table>
          <thead><tr><th>Kata</th><th>Jumlah</th></tr></thead>
          <tbody>
            {data.slice(0, 30).map((d) => (
              <tr key={d.kata}><td>{d.kata}</td><td>{d.jumlah}</td></tr>
            ))}
          </tbody>
        </table>
      </details>
    </>
  );
}
