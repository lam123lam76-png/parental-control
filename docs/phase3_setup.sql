-- ============================================================
-- PARENTAL CONTROL - PHASE 3 DATABASE UPDATE
-- ============================================================
-- Hướng dẫn:
-- 1. Mở Supabase Dashboard → SQL Editor → New Query
-- 2. Copy toàn bộ nội dung file này và bấm "Run"
-- ============================================================

-- 1. BẢNG LỊCH HỌC TẬP (schedules)
CREATE TABLE IF NOT EXISTS public.schedules (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    device_name TEXT NOT NULL,
    title TEXT NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    event_type TEXT NOT NULL DEFAULT 'study' CHECK (event_type IN ('study', 'play', 'rest')),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. BẢNG CHAT 2 CHIỀU (chat_messages)
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    device_name TEXT NOT NULL,
    sender TEXT NOT NULL CHECK (sender IN ('admin', 'student')),
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. BẢNG LỆNH ĐIỀU KHIỂN TỨC THÌ (system_commands)
CREATE TABLE IF NOT EXISTS public.system_commands (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    device_name TEXT NOT NULL,
    command TEXT NOT NULL CHECK (command IN ('take_screenshot', 'lock_screen', 'unlock_screen')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed')),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- RLS Security
ALTER TABLE public.schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.system_commands ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow all access to schedules" ON public.schedules;
DROP POLICY IF EXISTS "Allow all access to chat_messages" ON public.chat_messages;
DROP POLICY IF EXISTS "Allow all access to system_commands" ON public.system_commands;

CREATE POLICY "Allow all access to schedules" ON public.schedules FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access to chat_messages" ON public.chat_messages FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access to system_commands" ON public.system_commands FOR ALL USING (true) WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_schedules_device ON public.schedules (device_name, start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_chat_messages_device ON public.chat_messages (device_name, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_system_commands_device ON public.system_commands (device_name, status);
