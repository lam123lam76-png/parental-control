-- ============================================================
-- PARENTAL CONTROL - SUPABASE DATABASE SETUP (CLEAN INSTALL)
-- ============================================================
-- Hướng dẫn: 
-- 1. Mở Supabase Dashboard → SQL Editor → New Query
-- 2. Copy TOÀN BỘ nội dung file này
-- 3. Dán vào SQL Editor → nhấn "Run"
-- ============================================================

-- ============================
-- 0. XÓA CÁC BẢNG CŨ (Để tránh lỗi schema không khớp)
-- ============================
DROP TABLE IF EXISTS public.app_rules CASCADE;
DROP TABLE IF EXISTS public.time_restrictions CASCADE;
DROP TABLE IF EXISTS public.system_events CASCADE;
DROP TABLE IF EXISTS public.screenshot_logs CASCADE;
DROP TABLE IF EXISTS public.active_window_logs CASCADE;
DROP TABLE IF EXISTS public.process_logs CASCADE;
DROP TABLE IF EXISTS public.devices CASCADE;


-- ============================
-- 1. TẠO BẢNG MỚI
-- ============================

CREATE TABLE public.devices (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    device_name TEXT NOT NULL UNIQUE,
    is_online BOOLEAN DEFAULT false,
    last_seen TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE public.process_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    device_name TEXT NOT NULL,
    process_name TEXT NOT NULL,
    pid INTEGER,
    cpu_percent REAL DEFAULT 0,
    memory_mb REAL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_process_logs_device_time ON public.process_logs (device_name, created_at DESC);

CREATE TABLE public.active_window_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    device_name TEXT NOT NULL,
    process_name TEXT NOT NULL,
    window_title TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_active_window_device_time ON public.active_window_logs (device_name, created_at DESC);

CREATE TABLE public.screenshot_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    device_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_screenshot_device_time ON public.screenshot_logs (device_name, created_at DESC);

CREATE TABLE public.system_events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    device_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_system_events_device_time ON public.system_events (device_name, created_at DESC);

CREATE TABLE public.time_restrictions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    device_name TEXT NOT NULL,
    day_of_week INTEGER NOT NULL CHECK (day_of_week >= 0 AND day_of_week <= 6),
    start_time TIME NOT NULL DEFAULT '07:00:00',
    end_time TIME NOT NULL DEFAULT '21:00:00',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(device_name, day_of_week)
);

CREATE TABLE public.app_rules (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    device_name TEXT NOT NULL,
    process_name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'allowed' CHECK (category IN ('allowed', 'limited', 'forbidden')),
    max_minutes_per_day INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(device_name, process_name)
);
CREATE INDEX idx_app_rules_device ON public.app_rules (device_name, is_active);


-- ============================================================
-- 2. ROW LEVEL SECURITY (RLS)
-- ============================================================

ALTER TABLE public.devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.process_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.active_window_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.screenshot_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.system_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.time_restrictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.app_rules ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all access to devices" ON public.devices FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access to process_logs" ON public.process_logs FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access to active_window_logs" ON public.active_window_logs FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access to screenshot_logs" ON public.screenshot_logs FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access to system_events" ON public.system_events FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access to time_restrictions" ON public.time_restrictions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access to app_rules" ON public.app_rules FOR ALL USING (true) WITH CHECK (true);


-- ============================================================
-- 3. DỮ LIỆU MẶC ĐỊNH
-- ============================================================

INSERT INTO public.time_restrictions (device_name, day_of_week, start_time, end_time, is_active) VALUES
    ('May_Em_Trai', 0, '07:00:00', '21:00:00', true),
    ('May_Em_Trai', 1, '07:00:00', '21:00:00', true),
    ('May_Em_Trai', 2, '07:00:00', '21:00:00', true),
    ('May_Em_Trai', 3, '07:00:00', '21:00:00', true),
    ('May_Em_Trai', 4, '07:00:00', '21:00:00', true),
    ('May_Em_Trai', 5, '08:00:00', '22:00:00', true),
    ('May_Em_Trai', 6, '08:00:00', '22:00:00', true)
ON CONFLICT (device_name, day_of_week) DO NOTHING;

INSERT INTO public.app_rules (device_name, process_name, category, max_minutes_per_day, is_active) VALUES
    ('May_Em_Trai', 'chrome.exe', 'allowed', 0, true),
    ('May_Em_Trai', 'msedge.exe', 'allowed', 0, true),
    ('May_Em_Trai', 'WINWORD.EXE', 'allowed', 0, true),
    ('May_Em_Trai', 'EXCEL.EXE', 'allowed', 0, true),
    ('May_Em_Trai', 'POWERPNT.EXE', 'allowed', 0, true),
    ('May_Em_Trai', 'Code.exe', 'allowed', 0, true),
    ('May_Em_Trai', 'LeagueClient.exe', 'limited', 120, true),
    ('May_Em_Trai', 'RiotClientServices.exe', 'limited', 120, true),
    ('May_Em_Trai', 'GenshinImpact.exe', 'limited', 60, true),
    ('May_Em_Trai', 'steam.exe', 'limited', 90, true)
ON CONFLICT (device_name, process_name) DO NOTHING;
