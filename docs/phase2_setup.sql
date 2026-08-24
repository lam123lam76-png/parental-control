-- ============================================================
-- PARENTAL CONTROL - PHASE 2 DATABASE UPDATE (Option B)
-- ============================================================
-- Hướng dẫn:
-- 1. Mở Supabase Dashboard → SQL Editor → New Query
-- 2. Copy toàn bộ nội dung file này và nhấn "Run"
-- ============================================================

-- BẢNG: app_usage_logs
-- Đếm tổng số phút đã dùng của từng app theo từng ngày
CREATE TABLE IF NOT EXISTS public.app_usage_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    device_name TEXT NOT NULL,
    process_name TEXT NOT NULL,
    usage_date DATE NOT NULL DEFAULT CURRENT_DATE,
    used_minutes INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(device_name, process_name, usage_date)
);

-- RLS Security
ALTER TABLE public.app_usage_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow all access to app_usage_logs" ON public.app_usage_logs;
CREATE POLICY "Allow all access to app_usage_logs" ON public.app_usage_logs FOR ALL USING (true) WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_app_usage_date ON public.app_usage_logs (device_name, usage_date);
