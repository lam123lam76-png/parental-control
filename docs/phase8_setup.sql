-- ============================================================
-- PARENTAL CONTROL - PHASE 8 DATABASE UPDATE
-- Quyền truy cập & Mật khẩu tư cách
-- ============================================================
ALTER TABLE public.app_config ADD COLUMN IF NOT EXISTS role_passwords JSONB DEFAULT '{}'::jsonb;
ALTER TABLE public.app_config ADD COLUMN IF NOT EXISTS role_permissions JSONB DEFAULT '{}'::jsonb;
