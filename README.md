# sonnsonn

![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078D6)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB)

**Tekan satu tombol pintas, dapatkan jawaban untuk soal yang ada di layar.**
sonnsonn mengambil tangkapan layar, mengirimnya ke model AI, lalu memberi tahu
jawabannya lewat dua cara: **kedipan CapsLock** (A = 1 kedip … F = 6 kedip) dan
**kotak jawaban** kecil di pojok layar (opsional).

![sonnsonn menjawab soal pilihan ganda](docs/demo.png)

## Fitur

- **Satu tombol pintas** — tekan **F9**, layar utama diambil dan dikirim ke
  model. Tidak ada gambar yang disimpan ke disk.
- **Jawaban lewat CapsLock** — pilihan A–F dipetakan ke 1–6 kedipan, jadi
  jawaban bisa dibaca sekilas tanpa berpindah jendela. Pilihan tanpa huruf
  diurutkan sesuai tampilan: atas ke bawah, lalu kiri ke kanan.
- **Kotak jawaban opsional** — ukuran default 104 × 58 px, bisa diletakkan di
  lima posisi sudut, dan diskalakan 50–200 %. Kotak ini tidak pernah merebut
  fokus keyboard dan menutup sendiri.
- **Jawaban tertulis** — soal esai dan subpertanyaan a/b/c dijawab dalam bahasa
  yang sama dan disimpan ke `latest-answer.txt`.
- **Mode berpikir (thinking)** — tingkat penalaran off / low / high / max
  (default `high`), yang membuat soal hitungan dan soal bertahap jauh lebih
  akurat.
- **Pencarian web** — kalau soal bergantung pada informasi terkini, sonnsonn
  mengecek DeepSeek Search API lalu menjawab dari hasilnya.
- **Bisa pakai model sendiri** — endpoint apa pun yang kompatibel dengan
  OpenAI dan mendukung input gambar serta JSON mode.

## Kebutuhan

| | |
|---|---|
| Sistem operasi | Windows 10 atau 11 (hotkey dan kontrol CapsLock khusus Windows) |
| Python | 3.10 atau lebih baru (untuk instalasi dari source) |
| Akun | API key DeepSeek, atau endpoint vision apa pun yang kompatibel OpenAI |

## Instalasi cepat (disarankan)

1. Buka **[Releases](https://github.com/Hdiddz/sonn-sonn-display-answer/releases/latest)**
   lalu unduh **`sonnsonn.zip`**.
2. Ekstrak ke folder biasa yang bisa ditulis — misalnya
   `C:\Users\<nama>\Documents\sonnsonn`. Hindari `C:\Program Files`.
3. Klik dua kali **`sonnsonn.cmd`**. Saat pertama dijalankan, folder `.venv`
   dibuat dan dua dependensi dipasang (sekitar satu menit, butuh internet).
4. Di menu konsol pilih **`[6] API key`** lalu tempel API key DeepSeek Anda
   (ketikan disembunyikan). Key disimpan di `.env` di samping skrip.
5. Pilih **`[1]`** untuk menjalankan, lalu tekan **F9** pada soal apa pun.

Monitor tetap berjalan di background; jendela konsol menutup sendiri setelah
monitor aktif. Hentikan dengan `stop.cmd`.

## Instalasi manual dari source

```powershell
git clone https://github.com/Hdiddz/sonn-sonn-display-answer.git
cd sonn-sonn-display-answer
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\sonnsonn.cmd
```

Atau atur manual: salin `.env.example` menjadi `.env`, isi API key, lalu
jalankan `start.cmd`.

## Cara pakai

| Aksi | Caranya |
|---|---|
| Ambil gambar dan minta jawaban | tekan **F9** |
| Baca jawaban tertulis | klik dua kali `open-answer.cmd` |
| Hentikan monitor | klik dua kali `stop.cmd` |
| Ubah pengaturan | klik dua kali `sonnsonn.cmd` lagi (menu kontrol) |

Setiap capture mengirim **seluruh layar utama** ke API dan memakai kredit.
Tunggu jawaban muncul sebelum menekan F9 lagi; jawaban esai bisa memakan waktu
hingga 90 detik. Menahan tombol **Alt** membatalkan capture.

## Menu pengaturan

Menjalankan aplikasi saat monitor belum aktif akan membuka menu lengkap:

```
  CapsLock Monitor
    popup    : on
    position : bottom-left    scale: 100%
    thinking : high
    api key  : sk-4...e246
    model    : deepseek-flash  (https://api.deepseek.com)

    [1] Start - answer box + CapsLock flashes
    [2] Start - CapsLock flashes only
    [3] Popup position
    [4] Popup size
    [5] Thinking effort (off/low/high/max)
    [6] API key
    [7] Model / API base URL
    [8] Exit
```

Kalau dijalankan saat monitor **sudah aktif**, yang muncul adalah **menu
kontrol**: menghentikan monitor, menyembunyikan/menampilkan kotak, memindahkan,
mengubah ukuran, atau mengganti tingkat thinking — semuanya tanpa restart.

Label menu sengaja tetap bahasa Inggris agar cocok dengan tampilan aplikasi.

Pengaturan disimpan di `.monitor-settings` dan dibaca ulang pada setiap
jawaban, jadi perubahan langsung berlaku:

```ini
popup=on
position=bottom-left
scale=100
thinking=high
```

Posisi yang tersedia: `bottom-left`, `bottom-right`, `top-left`, `top-right`,
`center`. Skala: `50`–`200`.

## Sinyal jawaban

| Huruf | Kedipan CapsLock |
|---|---|
| A | 1 |
| B | 2 |
| C | 3 |
| D | 4 |
| E | 5 |
| F | 6 |

Jawaban tertulis dan status "tidak ada soal" memakai nada panjang/pendek yang
berbeda bila suara diaktifkan; build default senyap.

## Model dan penyedia

- Default: `deepseek-flash` di `https://api.deepseek.com`.
- **Thinking** diterjemahkan ke `thinking: enabled` milik DeepSeek ditambah
  `reasoning_effort` (`low` / `high` / `max`). Mode ini menaikkan batas balasan
  menjadi 8192 token karena token penalaran ikut dihitung. Thinking hanya
  tersedia di DeepSeek.
- **Penyedia lain**: isi base URL lewat menu `[7]` atau `DEEPSEEK_BASE_URL` di
  `.env`. Endpoint harus menerima konten `image_url` dan
  `response_format: json_object`. Thinking dan fitur pencarian dilewati di
  penyedia lain.

```ini
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

## Pencarian web

Kalau model menilai soal butuh informasi terkini, sonnsonn memanggil DeepSeek
Search API sekali, memasukkan hasil teratas, lalu menjawab ulang. Biayanya satu
permintaan pencarian ($0.75 per 1.000) ditambah satu permintaan teks tambahan.
Kalau pencarian gagal, jawaban pertama tetap dipakai. Matikan dengan
`DEEPSEEK_SEARCH=off` di `.env`.

## Pemecahan masalah

**F9 tidak bereaksi.** Jalankan aplikasi dari **Explorer Anda sendiri** atau
terminal biasa. Proses yang dijalankan oleh konteks otomasi/sandbox bisa berada
di *low integrity*, dan di kondisi itu Windows memblokir pembacaan keyboard.
`monitor.log` mencetak tingkat integrity saat mulai — harus tertulis
`integrity medium`. Coba juga **Fn+F9**: di banyak laptop baris fungsi berada
dalam mode media.

**Muncul "Monitor exited during startup".** Periksa `monitor.log` dan
`monitor-error.log` di folder aplikasi. Penyebab umumnya API key kosong atau
tidak valid.

**Kotak jawaban tidak muncul.** Pengaturan `popup=off` menyembunyikannya
(kedipan CapsLock tetap berjalan). Nyalakan lagi dari menu kontrol, pilihan
`[3]`.

**HTTP 401 / 402.** 401 berarti key salah; 402 berarti saldo akun habis.

**Jawaban hitungan salah.** Naikkan thinking ke `max` lewat menu `[5]`.

## Privasi

Tangkapan layar hanya disimpan di memori dan dikirim ke penyedia model yang
Anda atur; tidak pernah ditulis ke disk kecuali Anda memakai `--save-dir`.
Jawaban terakhir disimpan di `latest-answer.txt`, dan API key disimpan di
`.env` (keduanya di-ignore oleh Git).

## Penggunaan yang bertanggung jawab

sonnsonn adalah alat bantu membaca layar dan aksesibilitas. Gunakan hanya di
tempat yang memperbolehkan bantuan luar — bukan pada ujian, sertifikasi, atau
asesmen yang melarangnya, dan tidak dengan cara yang melanggar ketentuan
penyedia API Anda. Anda bertanggung jawab atas cara pemakaian dan atas jawaban
yang dihasilkan; jawaban AI bisa salah.

## Pengembangan

```powershell
.\.venv\Scripts\python.exe -m unittest test_monitor.py   # 38 tes, tanpa jaringan
.\.venv\Scripts\python.exe monitor.py --selftest          # cek logika cepat
```

`run_tests.py` adalah suite library tingkat rendah dan **mengubah LED CapsLock /
NumLock sungguhan** saat dijalankan.

| Berkas | Fungsi |
|---|---|
| `monitor.py` | loop hotkey, capture, panggilan API, pencarian, sinyal jawaban |
| `capture_popup.py` | kotak jawaban Win32 (posisi, skala, tanpa aktivasi) |
| `control.ps1` | konsol pengaturan dan kontrol di balik `sonnsonn.cmd` |
| `sonnsonn.cmd` / `start.cmd` / `stop.cmd` | launcher |
| `open-answer.cmd` | membuka jawaban terakhir |
| `demo.py` | mengedipkan teks Morse di LED lock |
| `test_monitor.py` | unit test |

## Lisensi

Belum ada lisensi. Sampai lisensi ditambahkan, hak cipta kode dipegang penuh
oleh penulis.
