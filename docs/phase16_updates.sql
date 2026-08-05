-- ============================================================
-- PARENTAL CONTROL - PHASE 16: CẬP NHẬT 04/08/2026
-- ============================================================
-- Chạy toàn bộ SQL này trên Supabase Dashboard → SQL Editor → New Query → Run
-- ============================================================

-- 1. THÊM CỘT is_allowed VÀO app_config (Task 1: Agent gọi lên kiểm tra quyền)
ALTER TABLE public.app_config ADD COLUMN IF NOT EXISTS is_allowed BOOLEAN DEFAULT true;

-- 2. THÊM CỘT time_limit_mode VÀO app_config (Task 4: Phương thức giới hạn giờ)
-- 'time_frame': theo khung giờ start_time ~ end_time (MẶC ĐỊNH)
-- 'max_daily': theo tổng thời gian tối đa/ngày (max_hours)
ALTER TABLE public.app_config ADD COLUMN IF NOT EXISTS time_limit_mode TEXT DEFAULT 'time_frame';

-- 3. ĐẢM BẢO BẢNG time_restrictions CÓ ĐỦ CỘT (start_time, end_time, max_hours)
ALTER TABLE public.time_restrictions ADD COLUMN IF NOT EXISTS start_time TIME DEFAULT '07:00:00';
ALTER TABLE public.time_restrictions ADD COLUMN IF NOT EXISTS end_time TIME DEFAULT '21:00:00';
ALTER TABLE public.time_restrictions ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;
ALTER TABLE public.time_restrictions ADD COLUMN IF NOT EXISTS max_hours INT DEFAULT 4;

-- 4. TẠO BẢNG agent_versions (Task 5: Cơ chế cập nhật từ xa)
CREATE TABLE IF NOT EXISTS public.agent_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version TEXT NOT NULL,
    file_path TEXT NOT NULL,
    changelog TEXT,
    uploaded_by TEXT DEFAULT 'admin',
    is_latest BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.agent_versions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow_All_agent_versions" ON public.agent_versions FOR ALL USING (true) WITH CHECK (true);

-- 5. TẠO BUCKET 'agent-updates' TRÊN SUPABASE STORAGE
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'agent-updates',
    'agent-updates',
    false,
    209715200,
    ARRAY['application/zip', 'application/x-zip-compressed']
)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "Allow upload to agent-updates"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'agent-updates');

CREATE POLICY "Allow read from agent-updates"
ON storage.objects FOR SELECT
USING (bucket_id = 'agent-updates');

CREATE POLICY "Allow delete from agent-updates"
ON storage.objects FOR DELETE
USING (bucket_id = 'agent-updates');

-- 6. CẬP NHẬT DỮ LIỆU MẶC ĐỊNH
INSERT INTO public.app_config (device_name, is_allowed, time_limit_mode)
VALUES ('May_Em_Trai', true, 'time_frame')
ON CONFLICT (device_name) DO UPDATE SET
    is_allowed = COALESCE(app_config.is_allowed, true),
    time_limit_mode = COALESCE(app_config.time_limit_mode, 'time_frame');

-- ============================================================
-- HOÀN TẤT! Tất cả cập nhật Phase 16 đã được áp dụng.
-- ============================================================
