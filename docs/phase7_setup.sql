-- ============================================================
-- PARENTAL CONTROL - PHASE 7 DATABASE UPDATE
-- Quản lý thiết bị truy cập & Phân quyền tư cách
-- ============================================================
CREATE TABLE IF NOT EXISTS public.web_access_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT UNIQUE NOT NULL,
    user_role TEXT DEFAULT 'Viewer',
    is_blocked BOOLEAN DEFAULT false,
    device_info TEXT,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

ALTER TABLE public.app_config ADD COLUMN IF NOT EXISTS custom_roles TEXT[] DEFAULT ARRAY['Em trai', 'Phụ huynh', 'Viewer'];
