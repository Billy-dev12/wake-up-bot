import json
import logging
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from config import AI_ENABLED, AI_MODEL, OPENROUTER_API_KEY

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def ai_enabled():
    return AI_ENABLED and OPENROUTER_API_KEY


def ask_ai(stats: dict, history: list):
    """Kirim data statistik ke OpenRouter AI, return analisis + motivasi."""
    if not ai_enabled():
        return None

    # Format history buat AI
    history_str = "\n".join(
        f"- {h['date']}: {h['status']} jam {h['time'] or '?'}"
        for h in history
    )

    prompt = f"""
KONTEKS & TEMA FITUR:
Ini PURE fitur WAKE-UP CHECKER. Target bangun jam 4 pagi (toleransi sampai jam 5 pagi).
JANGAN ngelantur ke tema lain (olahraga, kerja, dll) selain soal bangun pagi.
Data yang ada cuma status bangun/tidak bangun + jam jawab tiap hari.

SISTEM WAKE-UP:
- Status "bangun" = user klik tombol Bangun (anggap dia bangun).
- Status "tidak_bangun" = user ga bangun (ga respon, auto-marked, atau klik Tidak).
- ON TIME = jam jawab antara 04:00 sampai 05:59.
- TELAT = jam jawab jam 06:00 ke atas (bangun tapi kesiangan banget).

Berikut data wake-up history user (14 hari terakhir):
{history_str}

Statistik:
- Total hari terdata: {stats['total']}
- Kemenangan (bangun on time): {stats['wins']}
- Kekalahan (tidak bangun): {stats['losses']}
- Streak beruntun: {stats['streak']} hari

TUGAS KAMU (jawab bahasa Indonesia santai kayak temen, SINGKAT banget, maksimal 60 kata):
1. Perhatiin JAM pada tiap data. Respon harus beda-beda sesuai jam:
   - Kalo mayoritas jawab "bangun" di JAM 4-5 (on time) dan konsisten → PUJI keras, bilang "juara bangun subuh".
   - Kalo banyak yang "bangun" tapi JAM-nya TELAT (06:00 ke atas) → bilang kalo itu bukan on time, itu telat. Tegas tapi santai.
   - Kalo ada yang "bangun" tapi jam jawabnya janggal (misal jam 12 siang, jam 9 malam, atau jam nggak masuk akal) → curiga data keboongan. Bilang humoris tapi to the point bahwa user kayaknya nunyu tombol atau datanya bohong.
   - Kalo banyak "tidak_bangun" → kasih motivasi / semangat, bukan nge-judge.
2. Terakhir selalu tutup dengan SATU kalimat motivasi singkat biar user makin rajin bangun subuh.
3. Jangan formal. Pake bahasa gaul santai. Maksimal 1 emoji.
4. JAWAB LANGSUNG ke user. JANGAN jelasin proses mikir kamu, JANGAN pake nomor/step, JANGAN bilang "Analyze", "Draft", "Tutor", "Statistik", "Kesimpulan" dsb. Langsung kasih kata-kata santai doang, kayak lagi chat sama temen.

CONTOH POLA RESPON (langsung kayak gini, jangan ada label/penjelasan):
- On time semua: "Bro kamu legend banget, full subuh!! 🔥 Lanjutkan!"
- Suka telat: "Wuih bangun sih, tapi jam 8 bro, itu mah on time-nya telat wkwk."
- Jam aneh/bohong: "Eits, jam 11 siang bilang bangun? Ini mah pala kamu ga bangun, datanya kamu pencet ges."
- Banyak ga bangun: "Kemarin-kemarin berat ya bro, gapapa, hari ini gerak."
"""

    payload = json.dumps({
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "Analisis statistik wake-up ku bro"},
        ],
        "temperature": 0.7,
        # Token besar biar model reasoning ada ruang selesai mikir + jawab
        "max_tokens": 1500,
    }).encode("utf-8")

    req = Request(
        OPENROUTER_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://localhost",
            "X-Title": "Wake-Up Bot",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            msg = data["choices"][0]["message"]
            content = msg.get("content")

            if content and content.strip():
                return content.strip()

            # Kalau content kosong (model reasoning kepotong), jangan lempar
            # reasoning mentah. Ambil inti dari reasoning lalu rapikan singkat.
            raw = ""
            reasoning = msg.get("reasoning")
            if isinstance(reasoning, str):
                raw += reasoning
            details = msg.get("reasoning_details")
            if isinstance(details, list):
                raw += " ".join(
                    d.get("text", "") for d in details if isinstance(d, dict)
                )

            polished = _polish_reasoning(raw)
            return polished if polished else None

    except (HTTPError, URLError, KeyError, IndexError, AttributeError) as e:
        logger.error(f"AI request failed: {e}")
        return None


def _polish_reasoning(raw: str):
    """Ubah reasoning mentah jadi kalimat santai singkat, jangan panjang."""
    if not raw.strip():
        return None

    # Ambil bagian yang keliatan seperti draft jawaban akhir (paling akhir,
    # biasanya yang paling jadi)
    import re

    # Ambil kalimat dari bagian paling akhir yang bukan step/langkah analisis
    sentences = re.findall(r'[^.\n]+[.\n]', raw)
    good = [
        s.strip() for s in sentences
        if len(s.strip()) > 15 and not s.strip().lower().startswith(
            ("step", "langkah", "draft", "tutor", "sesuai", "conclusion",
             "kesimpulan", "tugas", "sistem", "analyze", "evaluate", "refining",
             "rule", "word count")
        )
    ]
    if not good:
        # fallback: lempar 2-3 kalimat terakhir aja
        tail = [s.strip() for s in sentences if s.strip()][-3:]
        return " ".join(tail)[:400] if tail else None

    # Ambil 1-2 kalimat terakhir yang paling kayak jawaban
    best = " ".join(good[-2:])
    return best[:400] if best else None
