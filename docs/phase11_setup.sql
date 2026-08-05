-- ============================================================
-- PARENTAL CONTROL - PHASE 11 WEB RULES & BLACK LIST DATABASE
-- ============================================================

CREATE TABLE IF NOT EXISTS public.web_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_name TEXT NOT NULL,
    domain TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'forbidden' CHECK (category IN ('allowed', 'limited', 'forbidden')),
    max_minutes_per_day INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(device_name, domain)
);

ALTER TABLE public.web_rules ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all access to web_rules" ON public.web_rules;
CREATE POLICY "Allow all access to web_rules" ON public.web_rules FOR ALL USING (true) WITH CHECK (true);
CREATE INDEX IF NOT EXISTS idx_web_rules_device ON public.web_rules (device_name);

CREATE TABLE IF NOT EXISTS public.web_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_name TEXT NOT NULL,
    domain TEXT NOT NULL,
    used_minutes INT DEFAULT 0,
    usage_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(device_name, domain, usage_date)
);

ALTER TABLE public.web_usage_logs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all access to web_usage_logs" ON public.web_usage_logs;
CREATE POLICY "Allow all access to web_usage_logs" ON public.web_usage_logs FOR ALL USING (true) WITH CHECK (true);
