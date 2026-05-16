-- migration 03: Subject Based Academic System

-- 1. Create teacher_subject_assignments table
CREATE TABLE IF NOT EXISTS public.teacher_subject_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID NOT NULL REFERENCES public.schools(id) ON DELETE CASCADE,
    teacher_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    class_id UUID NOT NULL REFERENCES public.classes(id) ON DELETE CASCADE,
    subject_id UUID NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(school_id, teacher_id, class_id, subject_id)
);

-- 2. Add subject_id to absensi
-- Check if column exists first to avoid error
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='absensi' AND column_name='subject_id') THEN
        ALTER TABLE public.absensi ADD COLUMN subject_id UUID REFERENCES public.subjects(id) ON DELETE SET NULL;
    END IF;
END $$;

-- 3. Fix absensi constraints for subject-based attendance
-- This allows one student to have attendance records for DIFFERENT subjects on the same day.
ALTER TABLE public.absensi DROP CONSTRAINT IF EXISTS absensi_student_id_date_key;
-- Check if the subject-based constraint already exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'absensi_student_subject_date_key') THEN
        ALTER TABLE public.absensi ADD CONSTRAINT absensi_student_subject_date_key UNIQUE (student_id, subject_id, date);
    END IF;
END $$;

-- 4. Enable RLS
ALTER TABLE public.teacher_subject_assignments ENABLE ROW LEVEL SECURITY;

-- 5. Policies for teacher_subject_assignments
DROP POLICY IF EXISTS "Enable read access for school members" ON public.teacher_subject_assignments;
CREATE POLICY "Enable read access for school members" ON public.teacher_subject_assignments
    FOR SELECT USING (
        school_id IN (
            SELECT school_id FROM public.user_schools WHERE user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Enable insert for admins" ON public.teacher_subject_assignments;
CREATE POLICY "Enable insert for admins" ON public.teacher_subject_assignments
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.profiles 
            WHERE id = auth.uid() AND role IN ('admin', 'owner')
        )
    );

DROP POLICY IF EXISTS "Enable delete for admins" ON public.teacher_subject_assignments;
CREATE POLICY "Enable delete for admins" ON public.teacher_subject_assignments
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM public.profiles 
            WHERE id = auth.uid() AND role IN ('admin', 'owner')
        )
    );
