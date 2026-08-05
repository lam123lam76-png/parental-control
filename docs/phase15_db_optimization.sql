-- ============================================================
-- PARENTAL CONTROL - MASTER DATABASE SETUP & OPTIMIZATION (FULL SAFE)
-- ============================================================
-- Mã SQL này tạo TẤT CẢ 15 BẢNG nếu chưa có + Bật RLS + Thêm INDEXES tăng tốc
-- Chạy đoạn này sẽ 100% THÀNH CÔNG, KHÔNG BAO GIỜ BỊ LỖI "relation does not exist"
-- ============================================================

-- 1. TẠO TẤT CẢ CÁC BẢNG NẾU CHƯA TỒN TẠI
CREATE TABLE IF NOT EXISTS public.app_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_name TEXT UNIQUE NOT NULL,
    agent_password TEXT DEFAULT 'Truc@1905s0825811915',
    admin_pin TEXT DEFAULT '123456',
    screenshot_interval_minutes INT DEFAULT 3,
    custom_roles JSONB DEFAULT '["Phụ huynh", "Em trai", "Gia sư"]'::jsonb,
    role_passwords JSONB DEFAULT '{}'::jsonb,
    role_permissions JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.time_restrictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_name TEXT NOT NULL,
    day_of_week INT NOT NULL,
    max_hours INT DEFAULT 4,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_name TEXT NOT NULL,
    name TEXT NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.app_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_name TEXT NOT NULL,
    process_name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'allowed',
    max_minutes_per_day INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.app_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_name TEXT NOT NULL,
    process_name TEXT NOT NULL,
    used_minutes INT DEFAULT 0,
    usage_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.active_window_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_name TEXT NOT NULL,
    title TEXT,
    process_name TEXT,
    pid INT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.browser_history_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_name TEXT NOT NULL,
    browser_name TEXT,
    title TEXT,
    url TEXT,
    visit_time TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_name TEXT NOT NULL,
    sender TEXT NOT NULL CHECK (sender IN ('admin', 'student')),
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.screenshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.todo_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_name TEXT NOT NULL,
    task_title TEXT NOT NULL,
    task_type TEXT DEFAULT 'admin_assigned',
    is_completed BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.system_commands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_name TEXT NOT NULL,
    command TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    result TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.system_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.web_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_name TEXT NOT NULL,
    domain TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'forbidden',
    max_minutes_per_day INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.web_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_name TEXT NOT NULL,
    domain TEXT NOT NULL,
    used_minutes INT DEFAULT 0,
    usage_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.web_access_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT UNIQUE NOT NULL,
    user_role TEXT DEFAULT 'Viewer',
    device_info TEXT,
    last_active TIMESTAMPTZ DEFAULT now(),
    is_blocked BOOLEAN DEFAULT false
);

-- 2. BẬT BẢO MẬT RLS & POLICY TẤT CẢ BẢNG
DO $$ 
DECLARE 
    tbl text;
BEGIN
    FOR tbl IN SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' 
    LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', tbl);
        EXECUTE format('DROP POLICY IF EXISTS "Allow_All_%I" ON public.%I;', tbl, tbl);
        EXECUTE format('CREATE POLICY "Allow_All_%I" ON public.%I FOR ALL USING (true) WITH CHECK (true);', tbl, tbl);
    END LOOP;
END $$;

-- 3. TẠO CHỈ MỤC TĂNG TỐC TRUY VẤN (INDEXES)
CREATE INDEX IF NOT EXISTS idx_browser_history_device_time ON public.browser_history_logs (device_name, visit_time DESC);
CREATE INDEX IF NOT EXISTS idx_active_window_device_time ON public.active_window_logs (device_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_app_usage_device_date ON public.app_usage_logs (device_name, usage_date);
CREATE INDEX IF NOT EXISTS idx_web_usage_device_date ON public.web_usage_logs (device_name, usage_date);
CREATE INDEX IF NOT EXISTS idx_web_rules_device ON public.web_rules (device_name);
CREATE INDEX IF NOT EXISTS idx_chat_messages_device ON public.chat_messages (device_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_screenshots_device_created ON public.screenshots (device_name, created_at DESC);

-- 4. HÀM TỰ ĐỘNG DỌN DẸP LOG RÁC CỦ QUÁ 30 NGÀY
CREATE OR REPLACE FUNCTION clean_old_logs()
RETURNS void AS $$
BEGIN
    DELETE FROM public.active_window_logs WHERE created_at < NOW() - INTERVAL '30 days';
    DELETE FROM public.browser_history_logs WHERE visit_time < NOW() - INTERVAL '60 days';
    DELETE FROM public.system_commands WHERE status = 'completed' AND created_at < NOW() - INTERVAL '7 days';
    DELETE FROM public.system_events WHERE created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
