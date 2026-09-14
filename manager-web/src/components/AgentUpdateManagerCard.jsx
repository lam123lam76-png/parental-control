import React, { useState, useEffect, useCallback } from "react";
import { api, uploadFileToR2 } from "../lib/api";
import { getThemeStyles } from "../lib/theme";
import { fmtBytes } from "../lib/utils";
import {
  Cpu,
  Rocket,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Sparkles,
  UploadCloud,
  ShieldCheck,
  Wifi,
  WifiOff,
} from "lucide-react";

/**
 * Quy Trình Đóng Gói & Cập Nhật Agent Từ Xa (kiến trúc cloud).
 *
 * CÁCH HOẠT ĐỘNG (đúng theo hạ tầng hiện tại: backend chạy trên Vercel, máy nhà
 * đã bỏ):
 *   1. Build gói ở máy dev: chạy `build_and_pack_agent.bat` (PyInstaller + zip).
 *   2. Tải gói .zip đó lên bucket R2 ngay trên thẻ này. Backend chỉ cấp URL PUT
 *      có chữ ký rồi ghi `version.json` (kèm SHA-256 do trình duyệt tính) —
 *      gói ~43 MB đi thẳng lên R2 vì Vercel function giới hạn body 4.5 MB.
 *   3. Bấm Phát Hành: backend đẩy lệnh `force_update` (đọc `version.json` từ R2)
 *      tới mọi máy đích. Máy đang bật nhận trong ~5 giây qua kênh poll; máy đang
 *      tắt sẽ nhận ngay khi bật lên lần sau.
 *
 * TRƯỚC ĐÂY HỎNG Ở ĐÂU (đã sửa): bước "Đóng gói" gọi API ghi zip ra đĩa của
 * server — đĩa Vercel là /tmp tạm thời và thư mục `agent/` không nằm trong bản
 * deploy nên luôn lỗi 500 "Agent directory not found", khiến nút Phát Hành bị
 * khoá vĩnh viễn; còn "phiên bản hiện tại" đọc file /tmp nên luôn hiện v0001 dù
 * bản thật là v0031.
 */
export default function AgentUpdateManagerCard({ theme = "dark" }) {
  const styles = getThemeStyles(theme);

  const [versionInfo, setVersionInfo] = useState(null);
  const [loadingVersion, setLoadingVersion] = useState(true);
  const [versionError, setVersionError] = useState("");
  const [newVersion, setNewVersion] = useState("");
  const [zipFile, setZipFile] = useState(null);
  const [phase, setPhase] = useState("idle"); // idle | hashing | uploading | publishing
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState(null); // { kind: "ok" | "err", text }
  const [deploying, setDeploying] = useState(false);
  const [deployResult, setDeployResult] = useState(null);
  const [r2Status, setR2Status] = useState(null);
  const [checkingR2, setCheckingR2] = useState(false);
  const [settingCors, setSettingCors] = useState(false);

  const suggestNextVersion = (currVer) => {
    const match = String(currVer || "").match(/v(\d+)/i);
    if (!match) return "v0001";
    return `v${String(parseInt(match[1], 10) + 1).padStart(4, "0")}`;
  };

  const loadVersion = useCallback(async () => {
    setLoadingVersion(true);
    setVersionError("");
    try {
      const res = await api.getAgentVersion();
      const data = res?.data || null;
      setVersionInfo(data);
      if (data?.version) setNewVersion(suggestNextVersion(data.version));
    } catch (err) {
      setVersionError(err.message || "Không đọc được phiên bản đang phát hành");
      setVersionInfo(null);
    } finally {
      setLoadingVersion(false);
    }
  }, []);

  useEffect(() => {
    loadVersion();
  }, [loadVersion]);

  const busy = phase !== "idle";
  const hasRelease = Boolean(versionInfo?.version && versionInfo?.source === "r2");
  const r2Configured = versionInfo?.r2_configured !== false;
  const nextVersion = suggestNextVersion(versionInfo?.version);
  const canUpload = Boolean(zipFile && newVersion.trim() && r2Configured);

  /** SHA-256 của file, tính ngay trên trình duyệt (máy đích dùng để kiểm tra gói). */
  const sha256OfFile = async (file) => {
    if (!window.crypto?.subtle) return ""; // http (không phải localhost) không có WebCrypto
    const buffer = await file.arrayBuffer();
    const digest = await window.crypto.subtle.digest("SHA-256", buffer);
    return Array.from(new Uint8Array(digest))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  };

  const handleUpload = async () => {
    if (!zipFile) {
      setMessage({ kind: "err", text: "Vui lòng chọn file .zip đã build (build_and_pack_agent.bat)." });
      return;
    }
    if (!newVersion.trim()) {
      setMessage({ kind: "err", text: "Vui lòng nhập số phiên bản (ví dụ: v0032)." });
      return;
    }

    setMessage(null);
    setDeployResult(null);
    setProgress(0);
    try {
      setPhase("hashing");
      const sha256 = await sha256OfFile(zipFile);

      setPhase("uploading");
      const presign = await api.presignAgentRelease(newVersion.trim());
      const presigned = presign.data;
      await uploadFileToR2(presigned.upload_url, zipFile, setProgress);

      setPhase("publishing");
      const published = await api.publishAgentRelease({
        version: presigned.version,
        sha256,
        size_bytes: zipFile.size,
      });

      setNewVersion(published.data.version);
      setZipFile(null);
      setPhase("idle");
      await loadVersion();

      const bits = [
        `Đã phát hành ${published.data.version} lên R2 (${fmtBytes(published.data.size_bytes)}).`,
        sha256
          ? "Gói có mã SHA-256 để máy đích tự kiểm tra."
          : "Chưa có SHA-256 (trình duyệt không hỗ trợ) — máy đích sẽ không kiểm tra được gói.",
      ];
      if (published.data.warning) bits.push(published.data.warning);
      setMessage({ kind: "ok", text: bits.join(" ") });
    } catch (err) {
      setPhase("idle");
      setMessage({ kind: "err", text: `Lỗi tải gói lên R2: ${err.message}` });
    }
  };

  const handleDeploy = async () => {
    const version = versionInfo?.version || "";
    const ok = window.confirm(
      `Phát hành ${version} tới TẤT CẢ máy đích?\n\n` +
        "• Máy đang bật: nhận lệnh trong ~5 giây, tự tải rồi cài lại Agent.\n" +
        "• Máy đang tắt: nhận ngay khi bật lên lần sau.\n\n" +
        "Chỉ nên phát hành khi gói trên R2 đã là bản mới nhất."
    );
    if (!ok) return;

    setDeploying(true);
    setDeployResult(null);
    try {
      const res = await api.forceUpdateAllDevices();
      const data = res?.data || {};
      setDeployResult(data);
      setMessage({
        kind: "ok",
        text:
          `Đã phát lệnh nâng cấp ${data.version || version}: ` +
          `${data.online_devices ?? 0} máy đang bật, ${data.offline_devices ?? 0} máy đang tắt ` +
          "(sẽ tự cài khi bật lên).",
      });
      await loadVersion();
    } catch (err) {
      setMessage({ kind: "err", text: `Lỗi phát hành: ${err.message}` });
    } finally {
      setDeploying(false);
    }
  };

  const handleCheckR2 = async () => {
    setCheckingR2(true);
    try {
      const res = await api.getAgentR2Status();
      setR2Status(res?.data || null);
    } catch (err) {
      setR2Status({ configured: false, error: err.message });
    } finally {
      setCheckingR2(false);
    }
  };

  const handleSetupCors = async () => {
    setSettingCors(true);
    try {
      const res = await api.setupAgentR2Cors();
      setMessage({ kind: "ok", text: res?.data?.msg || "Đã thiết lập CORS cho R2." });
      await handleCheckR2();
    } catch (err) {
      setMessage({ kind: "err", text: `Không thiết lập được CORS: ${err.message}` });
    } finally {
      setSettingCors(false);
    }
  };

  const phaseLabel = {
    hashing: "1/3 · Đang tính mã SHA-256 của gói…",
    uploading: `2/3 · Đang tải gói lên R2… ${progress}%`,
    publishing: "3/3 · Đang ghi version.json lên R2…",
  }[phase];

  const noticeClass = message?.kind === "err" ? styles.buttonDanger : styles.cardCallout;

  return (
    <div className={`p-4 sm:p-6 rounded-xl space-y-5 font-sans ${styles.card}`}>
      {/* HEADER */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className={`p-2.5 rounded-lg shrink-0 ${styles.chip}`}>
            <Cpu className="w-5 h-5 stroke-[1.75]" />
          </div>
          <div className="min-w-0">
            <h3 className={`text-sm font-bold truncate ${styles.textBold}`}>
              Quy Trình Đóng Gói &amp; Cập Nhật Agent Từ Xa
            </h3>
            <p className={`text-[11px] ${styles.textMuted}`}>
              Gói build được tải lên R2, máy đích tự tải về và cài ngầm
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={loadVersion}
          disabled={loadingVersion}
          title="Tải lại thông tin bản phát hành"
          className={`p-2 rounded-lg text-xs font-bold shrink-0 transition disabled:opacity-50 ${styles.buttonSecondary}`}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loadingVersion ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* MESSAGE */}
      {message && (
        <div className={`p-3.5 rounded-lg text-xs font-bold flex items-start gap-2.5 ${noticeClass}`}>
          {message.kind === "err" ? (
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          ) : (
            <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
          )}
          <span className="flex-1 leading-relaxed">{message.text}</span>
        </div>
      )}

      {!r2Configured && (
        <div className={`p-3.5 rounded-lg text-xs font-bold flex items-start gap-2.5 ${styles.buttonDanger}`}>
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span className="flex-1 leading-relaxed">
            Server chưa có R2_ACCESS_KEY / R2_SECRET_KEY nên chưa tải gói lên R2 được. Thêm 2 biến này
            vào Vercel (project quanlypc-api-backup) rồi deploy lại.
          </span>
        </div>
      )}

      {/* BẢN ĐANG PHÁT HÀNH (nguồn: R2) */}
      <div className={`p-4 rounded-xl ${styles.inset}`}>
        {loadingVersion ? (
          <div className={`text-xs ${styles.textMuted}`}>Đang đọc bản phát hành trên R2…</div>
        ) : versionError ? (
          <div className="flex items-center justify-between gap-3">
            <span className={`text-xs font-bold ${styles.statusOfflineText}`}>{versionError}</span>
            <button
              type="button"
              onClick={loadVersion}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold ${styles.buttonSecondary}`}
            >
              Thử lại
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <div className={`text-[10px] font-bold uppercase tracking-wider ${styles.metricLabel}`}>
                Bản đang phát hành trên R2
              </div>
              <div className={`text-lg font-extrabold flex items-center gap-2 mt-0.5 ${styles.metricValue}`}>
                <span>{versionInfo?.version || "—"}</span>
                {hasRelease ? (
                  <span className={`px-2 py-0.5 rounded text-[10px] tracking-wider ${styles.badge}`}>
                    SẴN SÀNG
                  </span>
                ) : (
                  <span className={`px-2 py-0.5 rounded text-[10px] tracking-wider ${styles.badgeMuted}`}>
                    CHƯA CÓ GÓI
                  </span>
                )}
              </div>
            </div>

            <div className="sm:text-right">
              <div className={`text-[10px] font-bold uppercase tracking-wider ${styles.metricLabel}`}>
                Dung lượng gói
              </div>
              <div className={`text-sm font-bold mt-0.5 ${styles.metricValue}`}>
                {fmtBytes(versionInfo?.size_bytes)}
              </div>
            </div>

            <div className="sm:col-span-2 space-y-1">
              <div className={`text-[10px] font-bold uppercase tracking-wider ${styles.metricLabel}`}>
                Mã kiểm tra gói (SHA-256)
              </div>
              <div className={`text-[11px] font-mono break-all ${styles.text}`}>
                {versionInfo?.sha256 || "— chưa có, máy đích sẽ không kiểm tra được gói"}
              </div>
            </div>

            <div className="sm:col-span-2 space-y-1">
              <div className={`text-[10px] font-bold uppercase tracking-wider ${styles.metricLabel}`}>
                Đường dẫn gói (máy đích tải về)
              </div>
              <a
                href={versionInfo?.public_url || "#"}
                target="_blank"
                rel="noreferrer"
                className={`block text-[11px] font-mono break-all underline ${styles.text}`}
              >
                {versionInfo?.public_url || "—"}
              </a>
            </div>

            {versionInfo?.created_at && (
              <div className={`sm:col-span-2 text-[11px] ${styles.textMuted}`}>
                Phát hành lúc: {new Date(versionInfo.created_at).toLocaleString("vi-VN")}
                {versionInfo.source === "local" && " · (đang đọc từ đĩa server — chế độ dev)"}
              </div>
            )}
          </div>
        )}
      </div>

      {/* BƯỚC 1: TẢI GÓI LÊN R2 */}
      <div className="space-y-3 pt-1">
        <div className="flex items-center justify-between gap-2">
          <label className={`text-xs font-bold uppercase tracking-wider ${styles.textBold}`}>
            1. Tải gói .zip lên R2
          </label>
          <button
            type="button"
            onClick={() => setNewVersion(nextVersion)}
            disabled={busy}
            className={`px-3 py-1.5 rounded-lg text-[11px] font-bold flex items-center gap-1.5 transition disabled:opacity-50 ${styles.buttonSecondary}`}
            title="Dùng phiên bản kế tiếp"
          >
            <Sparkles className="w-3 h-3" />
            Gợi ý: {nextVersion}
          </button>
        </div>

        <p className={`text-[11px] leading-relaxed ${styles.textMuted}`}>
          Chạy <span className="font-mono font-bold">build_and_pack_agent.bat</span> ở máy dev (nhớ tăng
          AGENT_VERSION), rồi chọn file{" "}
          <span className="font-mono font-bold">backend_api\storage\updates\agent-update.zip</span> ở đây.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <span className={`text-[10px] font-bold uppercase tracking-wider ${styles.metricLabel}`}>
              Số phiên bản mới
            </span>
            <input
              type="text"
              placeholder="v0032"
              value={newVersion}
              onChange={(e) => setNewVersion(e.target.value)}
              disabled={busy}
              className={`w-full p-3 text-sm font-bold font-mono rounded-xl focus:outline-none disabled:opacity-60 ${styles.input}`}
            />
          </div>

          <div className="space-y-1.5">
            <span className={`text-[10px] font-bold uppercase tracking-wider ${styles.metricLabel}`}>
              File gói (.zip)
            </span>
            <input
              type="file"
              accept=".zip,application/zip"
              onChange={(e) => setZipFile(e.target.files?.[0] || null)}
              disabled={busy}
              className={`w-full p-2 text-xs rounded-xl focus:outline-none disabled:opacity-60 ${styles.input}`}
            />
            {zipFile && (
              <div className={`text-[11px] ${styles.textMuted}`}>
                {zipFile.name} · {fmtBytes(zipFile.size)}
              </div>
            )}
          </div>
        </div>

        <button
          type="button"
          onClick={handleUpload}
          disabled={busy || !canUpload}
          className={`w-full p-4 rounded-xl text-sm font-bold flex items-center justify-center gap-2.5 transition disabled:opacity-50 disabled:cursor-not-allowed ${
            busy || !canUpload ? styles.buttonSecondary : styles.buttonPrimary
          }`}
        >
          <UploadCloud className={`w-4 h-4 ${busy ? "animate-pulse" : ""}`} />
          <span>{busy ? phaseLabel : "Tải Gói Lên R2"}</span>
        </button>

        {phase === "uploading" && (
          <div className={`h-2 w-full rounded-full overflow-hidden ${styles.inset}`}>
            <div
              className="h-full bg-emerald-500 transition-all duration-200"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
      </div>

      {/* BƯỚC 2: PHÁT HÀNH TỚI MÁY ĐÍCH */}
      <div className={`space-y-3 pt-4 border-t ${styles.divider}`}>
        <label className={`text-xs font-bold uppercase tracking-wider ${styles.textBold}`}>
          2. Phát hành &amp; cài trên máy đích
        </label>

        <div className="grid grid-cols-2 gap-3">
          <div className={`p-3 rounded-xl flex items-center gap-2.5 ${styles.chip}`}>
            <Wifi className={`w-4 h-4 shrink-0 ${styles.statusOnlineText}`} />
            <div className="min-w-0">
              <div className={`text-[10px] font-bold uppercase ${styles.metricLabel}`}>Máy đang bật</div>
              <div className={`text-sm font-extrabold ${styles.metricValue}`}>
                {deployResult ? deployResult.online_devices ?? 0 : "—"}
              </div>
            </div>
          </div>
          <div className={`p-3 rounded-xl flex items-center gap-2.5 ${styles.chip}`}>
            <WifiOff className={`w-4 h-4 shrink-0 ${styles.statusOfflineText}`} />
            <div className="min-w-0">
              <div className={`text-[10px] font-bold uppercase ${styles.metricLabel}`}>Máy đang tắt</div>
              <div className={`text-sm font-extrabold ${styles.metricValue}`}>
                {deployResult ? deployResult.offline_devices ?? 0 : "—"}
              </div>
            </div>
          </div>
        </div>

        <p className={`text-[11px] leading-relaxed ${styles.textMuted}`}>
          {deployResult
            ? `Đã xếp lệnh cho ${deployResult.queued ?? 0} máy. Máy đang tắt sẽ tự cài khi bật lên.`
            : "Số liệu máy bật/tắt hiện sau khi phát hành. Máy đang tắt vẫn nhận lệnh khi bật lên lần sau."}
        </p>

        <button
          type="button"
          onClick={handleDeploy}
          disabled={deploying || !hasRelease}
          className={`w-full p-4 rounded-xl text-sm font-bold flex items-center justify-center gap-2.5 transition disabled:opacity-50 disabled:cursor-not-allowed ${
            hasRelease ? styles.buttonSuccess : styles.buttonSecondary
          }`}
        >
          <Rocket className={`w-4 h-4 ${deploying ? "animate-spin" : ""}`} />
          <span>
            {deploying
              ? "Đang gửi lệnh tới máy đích…"
              : `Phát Hành ${versionInfo?.version || ""} Tới Tất Cả Máy`}
          </span>
        </button>

        {!hasRelease && (
          <p className={`text-[11px] font-bold ${styles.statusOfflineText}`}>
            Chưa có gói nào trên R2 — hãy hoàn tất bước 1 trước.
          </p>
        )}
      </div>

      {/* CHẨN ĐOÁN R2 */}
      <div className={`space-y-3 pt-4 border-t ${styles.divider}`}>
        <div className="flex items-center justify-between gap-2">
          <label className={`text-xs font-bold uppercase tracking-wider ${styles.textBold}`}>
            Kết nối R2
          </label>
          <button
            type="button"
            onClick={handleCheckR2}
            disabled={checkingR2}
            className={`px-3 py-1.5 rounded-lg text-[11px] font-bold flex items-center gap-1.5 transition disabled:opacity-50 ${styles.buttonSecondary}`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            {checkingR2 ? "Đang kiểm tra…" : "Kiểm tra kết nối R2"}
          </button>
        </div>

        {r2Status && (
          <div className={`p-3 rounded-xl text-[11px] space-y-2 ${styles.inset}`}>
            <div className={styles.text}>
              Token R2:{" "}
              <span className="font-bold">{r2Status.configured ? "đã cấu hình" : "chưa cấu hình"}</span>
              {" · "}Bucket: <span className="font-mono">{r2Status.bucket || "—"}</span>
              {" · "}Gói trong bucket: {fmtBytes(r2Status.zip_size_bytes)}
            </div>
            <div className={styles.text}>
              CORS cho trình duyệt:{" "}
              <span className="font-bold">
                {r2Status.cors_configured === true
                  ? "đã bật"
                  : r2Status.cors_configured === false
                  ? "chưa bật"
                  : "chưa rõ"}
              </span>
              {r2Status.cors_origins?.length ? ` (${r2Status.cors_origins.join(", ")})` : ""}
            </div>
            {r2Status.error && (
              <div className={`font-bold ${styles.statusOfflineText}`}>{r2Status.error}</div>
            )}

            {r2Status.configured && r2Status.cors_configured === false && (
              <button
                type="button"
                onClick={handleSetupCors}
                disabled={settingCors}
                className={`px-3 py-1.5 rounded-lg text-[11px] font-bold transition disabled:opacity-50 ${styles.buttonPrimary}`}
              >
                {settingCors ? "Đang thiết lập…" : "Thiết lập CORS cho R2"}
              </button>
            )}

            {r2Status.configured && r2Status.cors_configured !== true && (
              <div className="space-y-1.5">
                <div className={styles.text}>
                  Nếu nút trên báo <span className="font-mono">AccessDenied</span> (token chỉ có quyền
                  Object Read &amp; Write), hãy dán policy này vào Cloudflare → R2 → bucket{" "}
                  <span className="font-mono">{r2Status.bucket}</span> → Settings → CORS Policy:
                </div>
                <pre
                  className={`p-2 rounded-lg text-[10px] font-mono overflow-x-auto whitespace-pre ${styles.row}`}
                >
                  {r2Status.cors_policy_json}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
