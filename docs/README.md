# 📚 Ebsensi SaaS

> Sistem Absensi & Akademik Digital untuk Sekolah Islam — Dibangun dengan semangat oleh **Santri Mantap**

[![Python](https://img.shields.io/badge/Python-3.13-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-Latest-green)](https://flask.palletsprojects.com)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-orange)](https://supabase.com)
[![License](https://img.shields.io/badge/License-Zamify%20%C2%A9%202026-purple)](./LICENSE.md)

---

## 🌟 Tentang Proyek Ini

**Ebsensi SaaS** adalah platform manajemen sekolah Islam berbasis web yang dibangun sebagai proyek SaaS (Software as a Service) multi-tenant. Proyek ini lahir dari semangat para santri yang ingin memberikan solusi digital untuk pesantren dan sekolah Islam di Indonesia.

Dengan Ebsensi, setiap sekolah bisa:
- ✅ Mencatat absensi siswa per mata pelajaran
- 📖 Memantau hafalan Al-Quran santri
- 📊 Melihat laporan akademik secara real-time
- 👪 Memberikan akses dashboard kepada orang tua
- 🏫 Mengelola data guru, siswa, dan kelas dalam satu platform

---

## ✨ Fitur Utama

| Modul | Status | Deskripsi |
|-------|--------|-----------|
| 🏠 Dashboard | ✅ Aktif | Dashboard berbeda per role (Admin, Guru, Wali) |
| 📋 Absensi Per Mapel | ✅ Aktif | Catat kehadiran per mata pelajaran per hari |
| 📖 Hafalan Quran | ✅ Aktif | Input & tracking hafalan, murojaah, robert |
| 🕌 Halaqoh | ✅ Aktif | Manajemen grup belajar quran & nilai santri |
| 👪 Dashboard Wali | ✅ Aktif | Orang tua pantau absensi & hafalan anak |
| 📝 Ujian & Nilai | ✅ Aktif | Kelola ujian, input nilai, jenis ujian |
| 📌 Tugas | ✅ Aktif | Manajemen assignment per kelas & mapel |
| 💳 Subscription | ✅ Aktif | Paket Free/Basic/Premium dengan limit & fitur |
| 📅 Jadwal Pelajaran | 🔜 Soon | - |
| 💰 Keuangan | 🔜 Soon | - |
| 🖨️ Cetak Raport | 🔜 Soon | - |

---

## 🏗️ Arsitektur Sistem

```
ebsensi apk/
├── app.py                  # Entry point Flask — routes utama & konfigurasi
├── .env                    # Environment variables (JANGAN di-commit!)
│
├── auth/                   # Sistem autentikasi (middleware, service, repo)
├── database/migrations/    # SQL migrations (jalankan secara berurutan)
│
├── domains/                # Domain-Driven Design modules
│   ├── academic/           # Absensi, ujian, nilai, mata pelajaran
│   ├── auth/               # Onboarding sekolah baru
│   ├── halaqoh/            # Hafalan & halaqoh quran
│   ├── landing/            # Landing page publik
│   ├── subscriptions/      # Manajemen paket langganan
│   └── wali/               # Dashboard orang tua
│
├── templates/              # Jinja2 HTML templates
└── static/                 # CSS, JS, dan asset gambar
```

---

## 🚀 Cara Menjalankan

### Prasyarat
- Python 3.13+
- Akun Supabase (gratis di [supabase.com](https://supabase.com))

### Langkah Setup

**1. Clone repository**
```bash
git clone https://github.com/[USERNAME]/[REPO-NAME].git
cd ebsensi-saas
```

**2. Install dependencies**
```bash
pip install flask supabase python-dotenv werkzeug
```

**3. Konfigurasi environment**
```bash
cp .env.example .env
# Edit .env dengan kredensial Supabase kamu
```

**4. Jalankan database migrations**
```sql
-- Di Supabase SQL Editor, jalankan berurutan:
-- database/migrations/01_create_teacher_accounts.sql
-- database/migrations/02_multi_role_system.sql
-- database/migrations/03_subject_based_system.sql
```

**5. Jalankan aplikasi**
```bash
python app.py
```

Buka browser: `http://localhost:5000`

---

## ⚙️ Konfigurasi Environment

Buat file `.env` di root project:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
FLASK_SECRET_KEY=your_random_secret_key_min_32_chars
```

> ⚠️ **Penting:** Jangan pernah commit file `.env` ke Git!

Generate secret key yang aman:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## 👥 Role & Akses

| Role | Akses |
|------|-------|
| `admin` / `owner` | Semua fitur — kelola sekolah, guru, siswa, halaqoh |
| `guru (pengajar)` | Input absensi, kelola ujian & tugas per kelas |
| `guru (halaqoh)` | Input hafalan, kelola grup halaqoh |
| `wali` | Dashboard read-only — pantau anak |

---

## 🗺️ Alur Absensi Per Mata Pelajaran

```
Login Guru → Dashboard Pengajar
    ↓
Pilih Kelas (/academic/pilih-kelas)
    ↓
Pilih Mata Pelajaran (/academic/pilih-subject/<class_id>)
    ↓
Pilih Tanggal (/academic/pilih-tanggal/<class_id>/<subject_id>)
    ↓
Input Absensi Siswa (/academic/input-absensi/...)
    ↓
Data tersimpan di tabel 'absensi' (UNIQUE: student + subject + date)
```

---

## 📦 Paket Subscription

| Paket | Maks Siswa | Maks Guru | Fitur |
|-------|-----------|-----------|-------|
| Free | 20 | 2 | Fitur dasar |
| Basic | Custom | Custom | + Laporan |
| Premium | Custom | Custom | + Analytics + Dashboard Wali |

---

## 🤝 Kontribusi

Proyek ini dikembangkan oleh komunitas **Santri Mantap**. Untuk berkontribusi:

1. Fork repository ini
2. Buat branch baru: `git checkout -b fitur/nama-fitur`
3. Commit perubahan: `git commit -m "Tambah: nama fitur"`
4. Push ke branch: `git push origin fitur/nama-fitur`
5. Buat Pull Request

---

## 📄 Lisensi

Proyek ini dilindungi oleh lisensi **Zamify Proprietary License**.
Lihat file [LICENSE.md](./LICENSE.md) untuk detail lengkap.

Zamify © 2026 — All Rights Reserved.

---

## 📬 Kontak

GitHub: [Link akan ditambahkan]

---

*"Ilmu tanpa amal seperti pohon tanpa buah" — Dibuat dengan ❤️ oleh Santri Mantap*
