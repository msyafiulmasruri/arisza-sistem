"""Membuat gambar Word Cloud (pustaka wordcloud, pengaturan sama dengan notebook)."""
import io

WARNA = {"positive": "Greens", "neutral": "Blues", "negative": "Reds"}


def buat(teks, label):
    from wordcloud import WordCloud

    wc = WordCloud(
        width=1000, height=500, background_color="white",
        collocations=False, colormap=WARNA[label],
    ).generate(teks)
    buf = io.BytesIO()
    wc.to_image().save(buf, format="PNG")
    return buf.getvalue()
