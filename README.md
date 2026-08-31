# Wake-Up Bot 🌅

Bot Telegram yang ngecek kamu bangun pagi atau engga, lengkap dengan AI Coach dari OpenRouter.

## Fitur

- 🕐 **Wake-up reminder** — tiap jam 4 pagi kirim pesan + tombol "Bangun ✅" / "Tidak ❌"
- ⏳ **Auto-timeout** — kalo ga respon dalam X menit, otomatis dicatat "tidak bangun"
- 🏆 **Stats & streak** — `/stats` lihat kemenangan, streak, win rate
- 📋 **History** — `/history` 7 hari terakhir
- 🤖 **AI Coach** — `/stats` diiringin analisis OpenRouter yang deteksi jam keboongan + kasih motivasi
- ⌨️ **Bot commands menu** — `/` nongol di Telegram, auto-set tiap boot

## Struktur File

```
wake-up-bot/
├── bot.py            # Bot utama + handler + scheduler + error handler
├── ai_analyzer.py    # Integrasi OpenRouter AI (analisis + motivasi)
├── database.py       # SQLite operations
├── config.py         # Semua config (token, chat id, jam, timeout, AI)
├── requirements.txt  # Dependencies
├── wake_up.db        # Database (auto dibuat)
└── README.md         # Ini
```

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Konfigurasi `config.py`

Buka file `config.py` dan isi:

```python
# Telegram Bot Token dari @BotFather
BOT_TOKEN = "token_dari_botfather"

# Chat ID kamu (dapet dari @userinfobot di Telegram)
CHAT_ID = 1234567890

# Jam kirim (24 format)
WAKE_UP_HOUR = 4
WAKE_UP_MINUTE = 0

# Auto-timeout (menit)
TIMEOUT_MINUTES = 5

# OpenRouter AI (opsional)
OPENROUTER_API_KEY = "sk-or-v1-xxxxx"
AI_MODEL = "inclusionai/ling-3.0-flash-fin:free"
AI_ENABLED = True  # False kalo mau matiin AI
```

### 3. Jalankan
```bash
python bot.py
```

## Commands

| Command | Fungsi |
|---------|--------|
| `/start` | Info bot |
| `/stats` | Statistik + analisis AI Coach |
| `/history` | History 7 hari terakhir |
| `/test_send` | Test kirim pesan + test timeout |
| `/set_timeout [menit]` | Ganti timeout (5-360, default 5) |

## Cara Kerja

1. **Jam 4 pagi** → bot kirim pesan + tombol ✅❌
2. Terus 2 bot-nya schedule cek timeout (default **5 menit**)
3. Klik tombol → data tersimpan di SQLite (`wake_up.db`)
4. Ga respon dalam timeout → auto dicatat "tidak bangun"
5. `/stats` → statistik + AI analisis pola jam

## AI Coach (OpenRouter)

- Gratis, model default `inclusionai/ling-3.0-flash-fin:free`
- Deteksi pola:
  - `04:00–05:59` = on time → pujian
  - `06:00+` = telat → ditegur santai
  - Jam aneh (siang/malam) = curiga keboongan → dibilang humoris
  - Banyak "tidak_bangun" = dikasih semangat
- Ganti model di `AI_MODEL`, pilih gratis di [openrouter.ai/models](https://openrouter.ai/models)

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `run_daily() got unexpected keyword 'tzinfo'` | Pakai `dt_time(..., tzinfo=tz)` — sudah diperbaiki |
| AI output reasoning mentah/panjang | Sudah diperbaiki: naikin `max_tokens` + `_polish_reasoning` fallback |
| AI `content: None` | Model reasoning kepotong token → sekarang pakai fallback + token 1500 |
| `Command not found` | Cek token/chat id di config, restart bot |

## Catatan Keamanan ⚠️

- `BOT_TOKEN` dan `OPENROUTER_API_KEY` **ada di `config.py`** — JANGAN commit ke git publik / share.
- Pindahin ke environment variable buat lebih aman, atau tambah `config.py` ke `.gitignore`.

## Catatan Teknis

- Python 3.14, `python-telegram-bot` v20+
- Scheduler pakai APScheduler bawaan (`job_queue.run_daily`)
- Timezone: `Asia/Jakarta` (ubah di config)
- Database SQLite, file `wake_up.db` auto-buat tiap start
