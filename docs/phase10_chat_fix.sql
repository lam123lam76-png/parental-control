-- ============================================================
-- PARENTAL CONTROL - TẠO BẢNG CHAT VÀ SỬA LỖI TRUY CẬP SUPABASE
-- ============================================================

-- 1. TẠO BẢNG CHAT 2 CHIỀU (Nếu chưa có)
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    device_name TEXT NOT NULL,
    sender TEXT NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. BỎ CONSTRAINT GIỚI HẠN SENDER (Nếu có)
ALTER TABLE public.chat_messages DROP CONSTRAINT IF EXISTS chat_messages_sender_check;

-- 3. CẤP QUYỀN TRUY CẬP RLS CẢ CHUYỂN DỮ LIỆU
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all access to chat_messages" ON public.chat_messages;
CREATE POLICY "Allow all access to chat_messages" ON public.chat_messages FOR ALL USING (true) WITH CHECK (true);

-- 4. TẠO INDEX TỐC ĐỘ CHAT
CREATE INDEX IF NOT EXISTS idx_chat_messages_device ON public.chat_messages (device_name, created_at ASC);
