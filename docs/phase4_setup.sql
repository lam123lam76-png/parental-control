-- ============================================================
-- PARENTAL CONTROL - PHASE 4 DATABASE UPDATE (FIXED)
-- ============================================================

DROP TABLE IF EXISTS public.app_config CASCADE;

CREATE TABLE public.app_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_name TEXT NOT NULL UNIQUE,
    -- KHÔNG đặt mật khẩu mặc định trong SQL: repo này public nên mọi giá trị ở đây
    -- coi như đã lộ. Mật khẩu mở máy con do server cấp qua MASTER_UNLOCK_PASSWORD.
    agent_password TEXT,
    admin_pin TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.app_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all access to app_config" ON public.app_config FOR ALL USING (true) WITH CHECK (true);

-- Không seed sẵn mật khẩu/PIN: điền giá trị thật bằng biến môi trường hoặc giao diện quản trị.
INSERT INTO public.app_config (device_name)
VALUES ('May_Em_Trai');
