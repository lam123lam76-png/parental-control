import React from "react";
import { Lock, ShieldCheck, Monitor, Power, FileCode2 } from "lucide-react";
import { getThemeStyles } from "../lib/theme";

export default function SecurityHealthCards({ theme = "dark" }) {
  const styles = getThemeStyles(theme);

  return (
    <div className="space-y-6">
      
      {/* SECTION HEADER */}
      <div className="flex items-center justify-between">
        <h3 className={`text-sm font-bold flex items-center gap-2 ${styles.text}`}>
          <ShieldCheck className="w-4 h-4 stroke-[1.75]" />
          <span>Thẻ Kiểm Tra An Ninh & An Toàn Bảo Vệ Hệ Thống (Protection Layer)</span>
        </h3>
        <span className={`text-[10px] px-2 py-0.5 rounded ${styles.badge}`}>
          Security Health
        </span>
      </div>

      {/* SECURITY HEALTH CARDS GRID */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        {/* CARD 1: DPAPI ENCRYPTION STATUS */}
        <div className={`p-5 rounded-xl border space-y-3 ${styles.card}`}>
          <div className="flex items-center justify-between">
            <h4 className={`text-xs font-bold flex items-center gap-1.5 ${styles.textBold}`}>
              <Lock className="w-4 h-4 stroke-[1.75]" />
              <span>Mã Hóa Credential Bằng Windows DPAPI</span>
            </h4>
            <span className={`px-2 py-0.5 rounded text-[10px] font-mono ${styles.badge}`}>
              WIN32CRYPT ACTIVE
            </span>
          </div>

          

          <div className={`pt-2 border-t border-opacity-20 flex justify-between text-xs font-mono ${styles.text}`}>
            <span className="font-semibold">Dev Fallback Mode:</span>
            <span className={styles.textBold}>Disabled (Real DPAPI Enforced)</span>
          </div>
        </div>

        {/* CARD 2: HMAC FAIL-CLOSED INTEGRITY STATUS */}
        <div className={`p-5 rounded-xl border space-y-3 ${styles.card}`}>
          <div className="flex items-center justify-between">
            <h4 className={`text-xs font-bold flex items-center gap-1.5 ${styles.textBold}`}>
              <FileCode2 className="w-4 h-4 stroke-[1.75]" />
              <span>Chữ Ký HMAC-SHA256 Chống Sửa SQLite</span>
            </h4>
            <span className={`px-2 py-0.5 rounded text-[10px] font-mono ${styles.badge}`}>
              FAIL-CLOSED VALID
            </span>
          </div>

          

          <div className={`pt-2 border-t border-opacity-20 flex justify-between text-xs font-mono ${styles.text}`}>
            <span className="font-semibold">HMAC Integrity Signature:</span>
            <span className={styles.textBold}>Verified Match (Clean)</span>
          </div>
        </div>

        {/* CARD 3: MULTI-MONITOR BLOCKER OVERLAY */}
        <div className={`p-5 rounded-xl border space-y-3 ${styles.card}`}>
          <div className="flex items-center justify-between">
            <h4 className={`text-xs font-bold flex items-center gap-1.5 ${styles.textBold}`}>
              <Monitor className="w-4 h-4 stroke-[1.75]" />
              <span>Màn Hình Khóa Đa Màn Hình (Multi-Monitor Blocker)</span>
            </h4>
            <span className={`px-2 py-0.5 rounded text-[10px] font-mono ${styles.badge}`}>
              TKINTER ACTIVE
            </span>
          </div>

          

          <div className={`pt-2 border-t border-opacity-20 flex justify-between text-xs font-mono ${styles.text}`}>
            <span className="font-semibold">Phạm Vi Màn Hình:</span>
            <span className={styles.textBold}>Toàn Bộ Màn Hình (Auto-Enumerate)</span>
          </div>
        </div>

        {/* CARD 4: GRACEFUL SHUTDOWN & POWER BROADCAST */}
        <div className={`p-5 rounded-xl border space-y-3 ${styles.card}`}>
          <div className="flex items-center justify-between">
            <h4 className={`text-xs font-bold flex items-center gap-1.5 ${styles.textBold}`}>
              <Power className="w-4 h-4 stroke-[1.75]" />
              <span>Xử Lý Tắt Máy & Ngắt Kết Nối An Toàn</span>
            </h4>
            <span className={`px-2 py-0.5 rounded text-[10px] font-mono ${styles.badge}`}>
              HANDLERS ACTIVE
            </span>
          </div>

          

          <div className={`pt-2 border-t border-opacity-20 flex justify-between text-xs font-mono ${styles.text}`}>
            <span className="font-semibold">Last Shutdown Event:</span>
            <span className={styles.textBold}>Clean Disconnect Handler</span>
          </div>
        </div>

      </div>

    </div>
  );
}

