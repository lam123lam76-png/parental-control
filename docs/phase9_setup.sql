-- ============================================================
-- PARENTAL CONTROL - PHASE 9 BROWSER HISTORY LOGS
-- ============================================================
CREATE TABLE IF NOT EXISTS public.browser_history_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_name TEXT NOT NULL,
    browser_name TEXT DEFAULT 'Chrome',
    title TEXT,
    url TEXT,
    visit_time TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_browser_history_device ON public.browser_history_logs(device_name, visit_time DESC);
