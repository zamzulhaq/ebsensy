-- SQL Script untuk Update Tabel Mata Pelajaran (subjects)
-- Buka Supabase Dashboard -> SQL Editor -> New Query -> Jalankan script di bawah ini

-- 1. Tambahkan kolom-kolom baru
ALTER TABLE subjects
ADD COLUMN IF NOT EXISTS subject_code VARCHAR(50),
ADD COLUMN IF NOT EXISTS category VARCHAR(50) DEFAULT 'Akademik',
ADD COLUMN IF NOT EXISTS education_level VARCHAR(50) DEFAULT 'Semua Kelas',
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- 2. Pastikan kolom 'name' tetap ada sebagai nama mapel utama untuk backward compatibility
-- Kita tidak mengubah nama kolom 'name' menjadi 'subject_name' agar fitur absensi, nilai, dll tidak error.

-- 3. Beri komentar pada tabel untuk dokumentasi
COMMENT ON TABLE subjects IS 'Tabel Master Mata Pelajaran ERP Tahfidz';
COMMENT ON COLUMN subjects.category IS 'Kategori: Akademik, Tahfidz, Diniyah, Ekstrakurikuler';
COMMENT ON COLUMN subjects.is_active IS 'Soft delete flag: false berarti sudah diarsipkan';
