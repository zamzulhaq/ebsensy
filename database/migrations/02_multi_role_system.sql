-- Migration: Multi-Role System for Teachers
-- Created at: 2026-05-10

-- 1. Create teacher_roles table
CREATE TABLE IF NOT EXISTS public.teacher_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    teacher_id UUID NOT NULL REFERENCES public.teachers(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL, -- 'pengajar', 'halaqoh', 'admin'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(teacher_id, role)
);

-- 2. Migrate existing data from teachers.teacher_type
-- This ensures backward compatibility and moves current data to the new structure
INSERT INTO public.teacher_roles (teacher_id, role)
SELECT id, teacher_type 
FROM public.teachers 
WHERE teacher_type IS NOT NULL
ON CONFLICT (teacher_id, role) DO NOTHING;

-- 3. Create index for performance
CREATE INDEX IF NOT EXISTS idx_teacher_roles_teacher_id ON public.teacher_roles(teacher_id);
CREATE INDEX IF NOT EXISTS idx_teacher_roles_role ON public.teacher_roles(role);

-- Note: We keep teachers.teacher_type for backward compatibility as requested.
