"""Text preprocessing.

Isi fungsi ini SAMA dengan notebook (clean_text, normalize_text, final_cleaning)
agar teks baru diproses persis seperti data pelatihan.
"""
import html
import re

import emoji


def clean_text(text):
    text = html.unescape(str(text))
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"@[A-Za-z0-9_]+", " ", text)
    text = re.sub(r"#([A-Za-z0-9_]+)", r"\1", text)
    text = re.sub(r"<.*?>", " ", text)
    text = emoji.replace_emoji(text, replace=" ")
    text = re.sub(r"\b([A-Za-z]{3,})2\b", r"\1 \1", text)
    text = re.sub(r"\d+", " ", text)
    text = re.sub(r"[^A-Za-z!?\s]", " ", text)
    text = re.sub(r"!{2,}", "!", text)
    text = re.sub(r"\?{2,}", "?", text)
    text = re.sub(r"([A-Za-z])\1{2,}", r"\1\1", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_text(teks, kamus):
    def ganti_kata(match):
        kata = match.group(0)
        if re.fullmatch(r"gas{2,}", kata):
            return "ayo"
        return kamus.get(kata, kata)

    return re.sub(r"\b[a-z]+\b", ganti_kata, str(teks))


def final_cleaning(teks):
    teks = re.sub(r"[^a-zA-Z!?\s]", " ", str(teks))
    teks = re.sub(r"\s+", " ", teks)
    return teks.strip()


def preprocess(text, kamus):
    """Urutan sama dengan notebook: cleaning -> case folding -> normalization -> final cleaning."""
    text = clean_text(text)
    text = text.lower()
    text = normalize_text(text, kamus)
    return final_cleaning(text)
