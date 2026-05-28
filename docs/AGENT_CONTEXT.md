# EBSENSI SaaS — AI AGENT CONTEXT FILE
> Gunakan file ini sebagai konteks utama saat meminta AI agent menganalisis, menambah, atau mereview kode proyek Ebsensi SaaS.

---

## PROJECT IDENTITY

```
Nama Proyek     : Ebsensi SaaS APK
Jenis           : Multi-tenant SaaS — Sistem Absensi & Akademik Sekolah Islam
Framework       : Python Flask + Supabase (PostgreSQL + Auth)
Arsitektur      : Domain-Driven Design (DDD) dengan Blueprint Flask
Dibuat oleh     : Santri Mantap
Hak Cipta       : Zamify © 2026
Versi Analisis  : 1.0 — 28 Mei 2026
```

---

## STACK TEKNOLOGI

| Layer | Teknologi |
|-------|-----------|
| Backend | Python 3.13 + Flask |
| Database | Supabase (PostgreSQL) |
| Auth | Supabase Auth + Custom username/password hash |
| Frontend | Jinja2 Templates + Tailwind CSS |
| ORM/Query | Supabase Python SDK (langsung query tabel) |
| Deployment | Belum ditentukan (development: Flask dev server) |

---

## STRUKTUR DOMAIN

```
domains/
├── academic/       → Absensi per mapel, ujian, nilai, tugas, kelas
├── auth/           → Onboarding sekolah baru ke SaaS
├── halaqoh/        → Hafalan Al-Quran, nilai santri, ujian hafalan
├── landing/        → Landing page publik
├── subscriptions/  → Plan, limit siswa/guru, cek fitur
└── wali/           → Dashboard orang tua, pantau anak
```

---

## SISTEM AUTENTIKASI — 3 JALUR

| Jalur | User | Metode | File |
|-------|------|--------|------|
| A | Guru | Username + bcrypt hash | `auth/repository.py` → `teacher_accounts` |
| B | Admin/Wali | Email + Supabase Auth | `app.py` baris 260–315 |
| C | SaaS Users | Email + tabel `users` | `app.py` baris 228–260 |

---

## ROLE SYSTEM

```
admin   → Kelola semua data sekolah
owner   → Sama dengan admin (SaaS owner)
guru    → Sub-role: pengajar (akademik) atau halaqoh (quran)
wali    → Pantau siswa via dashboard orang tua
siswa   → (Belum aktif — placeholder)
```

---

## TABEL DATABASE UTAMA

```
schools                     → Master data sekolah (multi-tenant root)
teachers                    → Data guru (custom auth)
teacher_accounts            → Kredensial login guru (username + hash)
teacher_roles               → Multi-role guru
students                    → Data siswa
classes                     → Data kelas
subjects                    → Mata pelajaran
absensi                     → Catatan kehadiran (UNIQUE: student+subject+date)
hafalan                     → Catatan hafalan Al-Quran
halaqoh                     → Grup belajar quran
exam_types / exams          → Jenis & jadwal ujian
exam_scores                 → Nilai ujian per siswa
assignments                 → Tugas
weekly_targets              → Target hafalan mingguan per kelas
parent_student_relations    → Relasi wali ↔ siswa
profiles                    → Profil user Supabase Auth
user_schools                → Mapping user ↔ sekolah
school_subscriptions        → Langganan aktif per sekolah
subscription_plans          → Paket Free/Basic/Premium
```

---

## BLUEPRINT ROUTES

```
/               → landing_bp (domains/landing/routes.py)
/auth/*         → auth_bp (auth/routes.py)
/academic/*     → academic_bp (domains/academic/routes/academic_routes.py)
/halaqoh/*      → halaqoh_bp (domains/halaqoh/routes/halaqoh_routes.py)
/wali/*         → wali_bp (domains/wali/routes/wali_routes.py)
/subscriptions/ → subscriptions_bp
/onboarding/    → saas_auth_bp (domains/auth/routes/saas_auth_routes.py)
[43 route lain] → app.py langsung
```

---

## POLA KODE YANG DIGUNAKAN

### Repository Pattern
```python
# Setiap domain punya repo → service → route
repo = AcademicRepository(admin_supabase)
service = AcademicService(repo)
result = service.get_all_subjects(school_id)
```

### Auth Middleware
```python
# Gunakan dari auth/middleware.py (bukan auth/auth.py)
@login_required
@role_required("admin", "owner")
def my_route():
    ...
```

### Multi-Tenancy Isolation
```python
# WAJIB: Semua query harus filter school_id dari session
school_id = session.get('school_id')
result = db.table('students').select('*').eq('school_id', school_id).execute()
```

### Subscription Gate
```python
from domains.subscriptions.decorators.subscription_decorators import feature_required

@feature_required("analytics")
def analytics_page():
    ...
```

---

## RISIKO AKTIF (Belum Diperbaiki)

| ID | File | Masalah | Severity |
|----|------|---------|----------|
| R-01 | `.env` | Service role key & secret key terekspos | 🔴 KRITIS |
| R-02 | `app.py:1626` | `debug=True` aktif | 🔴 KRITIS |
| R-03 | `app.py` | `admin_supabase` overuse (86x, bypass RLS) | 🔴 KRITIS |
| R-04 | `app.py:228` | Login jalur B — konfirmasi hash password | 🔴 HIGH |
| W-01 | `auth/auth.py` | Duplikasi middleware dengan `auth/middleware.py` | 🟡 MED |
| W-02 | `migrations/03` | Status belum dikonfirmasi dijalankan | 🟡 MED |
| W-03 | `subscription_decorators.py` | `check_subscription_status()` isi `pass` | 🟡 MED |

---

## FITUR YANG BELUM SELESAI (Coming Soon)

```
/academic/jadwal    → Jadwal pelajaran
/academic/nilai     → Input nilai
/academic/raport    → Cetak raport
/academic/murojaah  → Murojaah santri
/finance            → Keuangan
/settings           → Pengaturan sistem
```

---

## KONVENSI YANG HARUS DIIKUTI SAAT TAMBAH KODE

1. **Selalu filter `school_id`** di setiap query database
2. **Gunakan `auth/middleware.py`** untuk decorator auth, bukan `auth/auth.py`
3. **Gunakan `admin_supabase` hanya** untuk operasi yang benar-benar butuh bypass RLS
4. **Ikuti pola** `Repository → Service → Route` saat tambah domain baru
5. **Tambah route baru** di domain Blueprint yang sesuai, bukan langsung di `app.py`
6. **Validasi input** di layer Service sebelum sampai ke Repository
7. **Flash message** pakai kategori: `success`, `danger`, `warning`

---

## FILE ANALISIS TERSEDIA

```
ANALISIS_MASTER_EBSENSI.txt   → Peta lengkap sistem, flow, risiko, skor
PETA_ROUTE_ENDPOINTS.txt      → Semua endpoint dengan auth level
PETA_DATABASE_TABEL.txt       → Semua tabel dan relasi
CHECKLIST_REVIEW_TIM.txt      → Checklist 25 item untuk sesi review
RISIKO_DAN_BREAKDOWN.txt      → Detail risiko + skenario bug production
```

---

*Ebsensi SaaS — Dibuat dengan semangat oleh Santri Mantap | Zamify © 2026*
