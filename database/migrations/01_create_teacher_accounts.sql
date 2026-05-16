-- Migration: Create teacher_accounts table

CREATE TABLE IF NOT EXISTS public.teacher_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    teacher_id UUID NOT NULL REFERENCES public.teachers(id) ON DELETE CASCADE,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    must_change_password BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Buat index untuk mempercepat pencarian username
CREATE INDEX IF NOT EXISTS idx_teacher_accounts_username ON public.teacher_accounts(username);
CREATE INDEX IF NOT EXISTS idx_teacher_accounts_teacher_id ON public.teacher_accounts(teacher_id);
