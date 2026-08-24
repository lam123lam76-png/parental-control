-- ============================================================
-- PARENTAL CONTROL - PHASE 4 DATABASE UPDATE (FIXED)
-- ============================================================

DROP TABLE IF EXISTS public.app_config CASCADE;

CREATE TABLE public.app_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_name TEXT NOT NULL UNIQUE,
    agent_password TEXT DEFAULT 'Truc@1905s0825811915',
    admin_pin TEXT DEFAULT '123456',
    updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.app_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all access to app_config" ON public.app_config FOR ALL USING (true) WITH CHECK (true);

INSERT INTO public.app_config (device_name, agent_password, admin_pin) 
VALUES ('May_Em_Trai', 'Truc@1905s0825811915', '123456');
