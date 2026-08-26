import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import { getThemeStyles } from "../lib/theme";
import { Users, UserPlus, Shield, Trash2, CheckCircle2, Lock, Eye, FileText, Monitor, Check, Settings } from "lucide-react";

export default function AccountPermissionsSettings({ theme = "dark", adminEmail = "" }) {
  const styles = getThemeStyles(theme);

  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  // Form State for creating Sub-Account
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [permissions, setPermissions] = useState({
    can_view_screenshots: true,
    can_manage_rules: true,
    can_view_logs: true,
    can_remote_control: true,
    can_manage_users: false,
  });

  // Fetch Sub-accounts
  const fetchSubAccounts = async () => {
    setLoading(true);
    try {
      const res = await api.getSubAccounts(adminEmail);
      if (res.data && Array.isArray(res.data.users)) {
        setUsers(res.data.users);
      }
    } catch (err) {
      setMessage(`Không thể tải danh sách tài khoản: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubAccounts();
  }, [adminEmail]);

  // Create Sub-Account Handler
  const handleCreateUser = async (e) => {
    e.preventDefault();
    if (!email || !password) return setMessage("Vui lòng nhập Email và Mật khẩu!");
    setLoading(true);
    setMessage("");

    try {
      await api.createSubAccount({
        email,
        password,
        admin_email: adminEmail,
        role: "sub_account",
        permissions,
      });
      setMessage(`Đã tạo thành công tài khoản phụ: ${email}`);
      setEmail("");
      setPassword("");
      fetchSubAccounts();
    } catch (err) {
      setMessage(`Lỗi tạo tài khoản: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Toggle permission for existing user
  const handleTogglePermission = async (userId, permKey, currentVal) => {
    const targetUser = users.find((u) => u.id === userId);
    if (!targetUser) return;

    const updatedPermissions = {
      ...targetUser.permissions,
      [permKey]: !currentVal,
    };

    // Optimistic UI update
    setUsers((prev) =>
      prev.map((u) =>
        u.id === userId ? { ...u, permissions: updatedPermissions } : u
      )
    );

    try {
      await api.updateUserPermissions(userId, updatedPermissions);
      setMessage(`Đã cập nhật phân quyền cho ${targetUser.email}`);
    } catch (err) {
      setMessage(`Lỗi cập nhật quyền: ${err.message}`);
      fetchSubAccounts(); // Rollback
    }
  };

  // Delete Sub-Account Handler
  const handleDeleteUser = async (userId, userEmail) => {
    if (!window.confirm(`Bạn có chắc chắn muốn xóa tài khoản phụ ${userEmail}?`)) return;
    try {
      await api.deleteSubAccount(userId);
      setMessage(`Đã xóa tài khoản: ${userEmail}`);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
    } catch (err) {
      setMessage(`Lỗi xóa tài khoản: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6 font-sans">
      
      {/* HEADER SECTION */}
      <div className={`p-4 sm:p-5 rounded-xl border flex items-center justify-between gap-3 ${styles.card}`}>
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-zinc-900/70 border border-zinc-800 border-l-2 border-l-[#064E3B] text-[#F8E7C9]">
            <Settings className="w-5 h-5 stroke-[1.75]" />
          </div>
          <div>
            <h2 className={`text-base font-extrabold ${styles.textBold}`}>
              Cài Đặt Hệ Thống & Quản Lý Tài Khoản Phụ
            </h2>
            <p className={`text-xs font-medium ${styles.textMuted}`}>
              Tạo tài khoản gia đình, quản lý bộ nhớ đĩa server, tự động dọn dẹp và cập nhật Agent từ xa.
            </p>
          </div>
        </div>
      </div>

      {message && (
        <div className="p-3 rounded-lg bg-zinc-900/70 border border-zinc-800 border-l-2 border-l-[#064E3B] text-xs text-[#F8E7C9] font-bold flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{message}</span>
        </div>
      )}

      {/* CREATE SUB-ACCOUNT FORM CARD */}
      <div className={`p-4 sm:p-5 rounded-xl border space-y-4 ${styles.card}`}>
        <h3 className={`text-sm font-bold flex items-center gap-2 ${styles.textBold}`}>
          <UserPlus className="w-4 h-4 stroke-[1.75] text-[#F8E7C9]" />
          <span>Thêm Tài Khoản Phụ Mới</span>
        </h3>

        <form onSubmit={handleCreateUser} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input
              type="email"
              placeholder="Email tài khoản phụ (ví dụ: mom@family.com)"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={`p-2.5 text-xs font-bold rounded-lg border focus:outline-none ${styles.input}`}
              required
            />
            <input
              type="password"
              placeholder="Mật khẩu khởi tạo"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={`p-2.5 text-xs font-bold rounded-lg border focus:outline-none ${styles.input}`}
              required
            />
          </div>

          {/* PERMISSIONS CHECKBOX GRID */}
          <div className="space-y-2">
            <label className={`text-xs font-bold uppercase tracking-wider block ${styles.textMuted}`}>
              CẤP QUYỀN TRUY CẬP (GRANULAR PERMISSIONS)
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 text-xs">
              {[
                { key: "can_view_screenshots", label: "Xem Ảnh Màn Hình", icon: Eye, desc: "Xem thư viện screenshot" },
                { key: "can_manage_rules", label: "Quản Lý Quy Tắc Cấm", icon: Shield, desc: "Thêm/Xóa luật App/Web" },
                { key: "can_view_logs", label: "Xem Nhật Ký Tiến Trình", icon: FileText, desc: "Xem lịch sử ứng dụng" },
                { key: "can_remote_control", label: "Điều Khiển Từ Xa", icon: Monitor, desc: "Khóa/Mở/Chụp màn hình" },
                { key: "can_manage_users", label: "Quản Lý Phân Quyền", icon: Lock, desc: "Tạo & Phân quyền user khác" },
              ].map((perm) => {
                const IconComp = perm.icon;
                const isChecked = permissions[perm.key];
                return (
                  <div
                    key={perm.key}
                    onClick={() =>
                      setPermissions((prev) => ({ ...prev, [perm.key]: !isChecked }))
                    }
                    className={`p-3 rounded-lg border cursor-pointer flex items-center justify-between transition ${
                      isChecked
                        ? "bg-[#064E3B]/20 border-[#064E3B] text-[#F8E7C9]"
                        : styles.card + " opacity-60 hover:opacity-100"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <IconComp className="w-4 h-4 text-emerald-400" />
                      <div>
                        <div className="font-bold text-xs">{perm.label}</div>
                        <div className={`text-[10px] ${styles.textMuted}`}>{perm.desc}</div>
                      </div>
                    </div>
                    <div className={`w-4 h-4 rounded border flex items-center justify-center ${
                      isChecked ? "bg-[#064E3B] border-[#F8E7C9] text-white" : "border-zinc-600"
                    }`}>
                      {isChecked && <Check className="w-3 h-3 stroke-[2.5]" />}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className={`w-full py-2.5 text-xs font-bold rounded-lg transition ${styles.buttonPrimary} disabled:opacity-50`}
          >
            {loading ? "Đang xử lý..." : "Tạo & Cấp Quyền Tài Khoản Phụ"}
          </button>
        </form>
      </div>

      {/* SUB-ACCOUNTS LIST CARD */}
      <div className={`p-4 sm:p-5 rounded-xl border space-y-4 ${styles.card}`}>
        <h3 className={`text-sm font-bold flex items-center gap-2 ${styles.textBold}`}>
          <Users className="w-4 h-4 stroke-[1.75] text-[#F8E7C9]" />
          <span>Danh Sách Tài Khoản Trong Gia Đình ({users.length})</span>
        </h3>

        {users.length === 0 ? (
          <p className={`text-xs italic text-center py-6 ${styles.textMuted}`}>
            Chưa có tài khoản phụ nào. Hãy thêm tài khoản ở form trên.
          </p>
        ) : (
          <div className="space-y-3">
            {users.map((u) => (
              <div
                key={u.id}
                className={`p-4 rounded-xl border space-y-3 transition ${styles.card}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                    <div>
                      <span className={`font-bold text-xs ${styles.textBold}`}>{u.email}</span>
                      <div className="flex items-center gap-2 text-[10px] text-zinc-400 mt-0.5">
                        <span className="px-2 py-0.5 rounded bg-[#064E3B]/30 border border-zinc-800 font-bold uppercase text-[#F8E7C9]">
                          {u.role}
                        </span>
                        <span>Khởi tạo: {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}</span>
                      </div>
                    </div>
                  </div>

                  {u.role !== "admin" && (
                    <button
                      onClick={() => handleDeleteUser(u.id, u.email)}
                      className="p-1.5 rounded-lg bg-rose-900/30 border border-rose-800/50 text-rose-300 hover:bg-rose-900/60 transition"
                      title="Xóa tài khoản này"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>

                {/* Granular Permission Toggles */}
                <div className="pt-2 border-t border-opacity-20 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 text-[11px]">
                  {[
                    { key: "can_view_screenshots", label: "Ảnh Màn Hình" },
                    { key: "can_manage_rules", label: "Quy Tắc Cấm" },
                    { key: "can_view_logs", label: "Nhật Ký Log" },
                    { key: "can_remote_control", label: "Điều Khiển" },
                    { key: "can_manage_users", label: "Phân Quyền" },
                  ].map((p) => {
                    const isAllowed = u.permissions?.[p.key] ?? true;
                    const isAdmin = u.role === "admin";
                    return (
                      <button
                        key={p.key}
                        disabled={isAdmin}
                        onClick={() => handleTogglePermission(u.id, p.key, isAllowed)}
                        className={`p-2 rounded-lg border text-left transition flex items-center justify-between ${
                          isAllowed
                            ? "bg-zinc-900/70 border border-zinc-800 border-l-2 border-l-[#064E3B] text-[#F8E7C9]"
                            : "bg-rose-900/10 border-rose-900/30 text-rose-300 opacity-70"
                        } ${isAdmin ? "cursor-not-allowed opacity-90" : "hover:border-emerald-500"}`}
                      >
                        <span className="font-bold truncate">{p.label}</span>
                        <span className={`text-[9px] font-extrabold px-1.5 py-0.5 rounded ${
                          isAllowed ? "bg-[#064E3B] text-[#F8E7C9]" : "bg-rose-900/40 text-rose-300"
                        }`}>
                          {isAllowed ? "BẬT" : "TẮT"}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  );
}
