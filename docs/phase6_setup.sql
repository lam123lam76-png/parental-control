-- ============================================================
-- PARENTAL CONTROL - PHASE 6 DATABASE UPDATE (Screenshot Interval)
-- ============================================================
ALTER TABLE public.app_config ADD COLUMN IF NOT EXISTS screenshot_interval_minutes INTEGER DEFAULT 3;
