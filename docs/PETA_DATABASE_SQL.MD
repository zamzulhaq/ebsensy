# PETA_DATABASE.md

# EBSENSY — DATABASE SOURCE OF TRUTH

Dokumen ini adalah referensi resmi struktur database project Ebsensy.

WAJIB dibaca sebelum:

* membuat query
* membuat fitur baru
* membuat migration
* membuat relation baru
* membuat API/service/repository

---

# RULES WAJIB

## 1. DILARANG HALUSINASI SCHEMA

WAJIB gunakan:

* nama table asli
* nama field asli
* relation asli

DILARANG:

* membuat table baru tanpa approval
* rename field sembarangan
* duplicate logic
* duplicate relation

---

## 2. WAJIB MULTI-TENANT

SEMUA query wajib memperhatikan:

```sql
school_id
```

Karena sistem menggunakan:

# SaaS Multi School Architecture

Contoh benar:

```sql
SELECT * FROM students
WHERE school_id = ?
```

Contoh salah:

```sql
SELECT * FROM students
```

---

# DATABASE CORE STRUCTURE

---

# TABLE: schools

Master data sekolah / tenant SaaS.

| Field             | Type      | Description     |
| ----------------- | --------- | --------------- |
| id                | uuid      | primary key     |
| name              | text      | nama sekolah    |
| subscription_plan | text      | paket langganan |
| created_at        | timestamp | waktu dibuat    |

---

# TABLE: users

Master akun login sistem.

| Field         | Type      | Description    |
| ------------- | --------- | -------------- |
| id            | uuid      | primary key    |
| school_id     | uuid      | tenant sekolah |
| full_name     | text      | nama user      |
| email         | text      | email login    |
| password_hash | text      | password hash  |
| role          | text      | role utama     |
| created_at    | timestamp | waktu dibuat   |

---

# TABLE: teachers

Master data guru / ustadz.

| Field      | Type      | Description     |
| ---------- | --------- | --------------- |
| id         | uuid      | primary key     |
| school_id  | uuid      | tenant sekolah  |
| user_id    | uuid      | relasi ke users |
| full_name  | text      | nama guru       |
| gender     | text      | gender guru     |
| created_at | timestamp | waktu dibuat    |

---

# TABLE: students

Master data siswa/santri.

| Field      | Type      | Description       |
| ---------- | --------- | ----------------- |
| id         | uuid      | primary key       |
| school_id  | uuid      | tenant sekolah    |
| class_id   | uuid      | relasi kelas      |
| full_name  | text      | nama siswa        |
| nis        | text      | nomor induk siswa |
| gender     | text      | gender siswa      |
| created_at | timestamp | waktu dibuat      |

---

# TABLE: classes

Master data kelas.

| Field               | Type      | Description    |
| ------------------- | --------- | -------------- |
| id                  | uuid      | primary key    |
| school_id           | uuid      | tenant sekolah |
| class_name          | text      | nama kelas     |
| homeroom_teacher_id | uuid      | wali kelas     |
| created_at          | timestamp | waktu dibuat   |

---

# TABLE: subjects

Master mata pelajaran.

| Field           | Type      | Description      |
| --------------- | --------- | ---------------- |
| id              | uuid      | primary key      |
| school_id       | uuid      | tenant sekolah   |
| subject_name    | text      | nama pelajaran   |
| subject_code    | text      | kode mapel       |
| category        | text      | akademik/halaqoh |
| education_level | text      | jenjang          |
| created_at      | timestamp | waktu dibuat     |

---

# TABLE: teacher_subjects

Relasi guru dengan mata pelajaran.

| Field      | Type | Description  |
| ---------- | ---- | ------------ |
| id         | uuid | primary key  |
| teacher_id | uuid | relasi guru  |
| subject_id | uuid | relasi mapel |
| class_id   | uuid | relasi kelas |

---

# TABLE: attendance_sessions

Session absensi per pelajaran.

| Field           | Type      | Description     |
| --------------- | --------- | --------------- |
| id              | uuid      | primary key     |
| school_id       | uuid      | tenant sekolah  |
| class_id        | uuid      | kelas           |
| subject_id      | uuid      | mapel           |
| teacher_id      | uuid      | guru            |
| attendance_date | date      | tanggal absensi |
| created_at      | timestamp | waktu dibuat    |

---

# TABLE: attendances

Data absensi siswa.

| Field                 | Type | Description           |
| --------------------- | ---- | --------------------- |
| id                    | uuid | primary key           |
| attendance_session_id | uuid | relasi session        |
| student_id            | uuid | siswa                 |
| status                | text | hadir/sakit/izin/alpa |
| notes                 | text | catatan guru          |

---

# TABLE: exams

Master ujian.

| Field      | Type      | Description    |
| ---------- | --------- | -------------- |
| id         | uuid      | primary key    |
| school_id  | uuid      | tenant sekolah |
| class_id   | uuid      | kelas          |
| subject_id | uuid      | mapel          |
| title      | text      | nama ujian     |
| exam_date  | date      | tanggal ujian  |
| created_at | timestamp | waktu dibuat   |

---

# TABLE: exam_scores

Nilai ujian siswa.

| Field      | Type    | Description  |
| ---------- | ------- | ------------ |
| id         | uuid    | primary key  |
| exam_id    | uuid    | relasi ujian |
| student_id | uuid    | siswa        |
| score      | numeric | nilai        |

---

# TABLE: halaqoh_groups

Master halaqoh.

| Field        | Type | Description    |
| ------------ | ---- | -------------- |
| id           | uuid | primary key    |
| school_id    | uuid | tenant sekolah |
| halaqoh_name | text | nama halaqoh   |
| musyrif_id   | uuid | pembimbing     |

---

# TABLE: hafalan_records

Riwayat hafalan santri.

| Field      | Type      | Description      |
| ---------- | --------- | ---------------- |
| id         | uuid      | primary key      |
| school_id  | uuid      | tenant sekolah   |
| student_id | uuid      | siswa            |
| surah_name | text      | nama surat       |
| ayat_start | int       | ayat awal        |
| ayat_end   | int       | ayat akhir       |
| grade      | text      | kualitas hafalan |
| notes      | text      | catatan          |
| created_at | timestamp | waktu dibuat     |

---

# TABLE RELATION MAP

students.class_id
→ classes.id

teacher_subjects.teacher_id
→ teachers.id

teacher_subjects.subject_id
→ subjects.id

teacher_subjects.class_id
→ classes.id

attendance_sessions.class_id
→ classes.id

attendance_sessions.subject_id
→ subjects.id

attendance_sessions.teacher_id
→ teachers.id

attendances.attendance_session_id
→ attendance_sessions.id

attendances.student_id
→ students.id

exam_scores.exam_id
→ exams.id

exam_scores.student_id
→ students.id

hafalan_records.student_id
→ students.id

---

# ARCHITECTURE RULES

## Academic Domain

Mengelola:

* absensi
* ujian
* nilai
* raport akademik

## Halaqoh Domain

Mengelola:

* hafalan
* setoran
* halaqoh
* raport tahfidz

## Wali Domain

Mengelola:

* monitoring wali murid
* dashboard wali
* perkembangan siswa

## Subscription Domain

Mengelola:

* SaaS billing
* paket langganan
* feature gating

---

# SECURITY RULES

* WAJIB validasi school_id
* DILARANG bypass tenant isolation
* DILARANG expose service_role_key
* WAJIB gunakan RLS jika memungkinkan

---

# DEVELOPMENT RULES

## Sebelum membuat fitur:

1. cek schema
2. cek relation
3. cek existing logic
4. cek repository/service terkait

## DILARANG:

* query random langsung di route
* business logic di template
* duplicate repository
* duplicate query

---

# STATUS PROJECT

Project ini menggunakan:

* Flask
* Supabase
* PostgreSQL
* Multi-Tenant SaaS Architecture
* Modular ERP Architecture

---

# FINAL NOTE

Dokumen ini adalah:

# SOURCE OF TRUTH DATABASE

Semua developer dan AI assistant WAJIB mengikuti struktur ini.
