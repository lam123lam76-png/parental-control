-- ============================================================
-- PARENTAL CONTROL - PHASE 5 DATABASE UPDATE (To Do Notes)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.todo_notes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    device_name TEXT NOT NULL,
    task_title TEXT NOT NULL,
    task_type TEXT NOT NULL DEFAULT 'admin_assigned' CHECK (task_type IN ('admin_assigned', 'routine')),
    is_completed BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.todo_notes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all access to todo_notes" ON public.todo_notes;
CREATE POLICY "Allow all access to todo_notes" ON public.todo_notes FOR ALL USING (true) WITH CHECK (true);

-- Dữ liệu To Do Note mẫu
INSERT INTO public.todo_notes (device_name, task_title, task_type, is_completed) VALUES
    ('May_Em_Trai', 'Hoàn thành bài tập Toán đại số chương 3', 'admin_assigned', false),
    ('May_Em_Trai', 'Đọc 15 trang sách Tiếng Anh', 'admin_assigned', false),
    ('May_Em_Trai', 'Học từ vựng Tiếng Anh theo thời gian biểu', 'routine', false),
    ('May_Em_Trai', 'Ôn tập lý thuyết Vật Lý 30 phút', 'routine', true);
