import React from "react";
import { Builder } from "@builder.io/react";
import { BarChart3, BellRing, ShieldCheck, Smartphone, Sparkles, Users } from "lucide-react";
import { getBuilderEditorLabel } from "./mode";

function StatTile({ label, value, tone = "emerald" }) {
  const tones = {
    emerald: "border-emerald-400/30 bg-emerald-400/10 text-emerald-100",
    amber: "border-amber-400/30 bg-amber-400/10 text-amber-100",
    sky: "border-sky-400/30 bg-sky-400/10 text-sky-100",
    rose: "border-rose-400/30 bg-rose-400/10 text-rose-100",
  };

  return (
    <div className={`rounded-2xl border p-4 shadow-lg ${tones[tone]}`}>
      <div className="text-[11px] uppercase tracking-[0.24em] opacity-80">{label}</div>
      <div className="mt-2 text-2xl font-semibold leading-none">{value}</div>
    </div>
  );
}

function SectionCard({ eyebrow, title, description, children }) {
  return (
    <section className="rounded-[28px] border border-white/10 bg-white/6 p-5 shadow-[0_24px_80px_rgba(0,0,0,0.35)] backdrop-blur">
      <div className="mb-4 space-y-1">
        <div className="text-[11px] uppercase tracking-[0.28em] text-emerald-200/80">{eyebrow}</div>
        <h3 className="text-xl font-semibold text-white">{title}</h3>
        <p className="text-sm leading-6 text-zinc-300">{description}</p>
      </div>
      {children}
    </section>
  );
}

export function BuilderTopBanner({
  heading = "Admin Dashboard",
  subtitle = "Builder Preview Mode đã bật. Bạn có thể đổi chữ, màu và bố cục mà không đụng vào luồng xác thực thật.",
  badge = "Builder Preview Mode",
}) {
  return (
    <header className="rounded-[32px] border border-white/10 bg-black/30 p-6 shadow-2xl backdrop-blur">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-3 max-w-3xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-[11px] uppercase tracking-[0.24em] text-emerald-100">
            <Sparkles className="h-3.5 w-3.5" />
            {badge}
          </div>
          <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">{heading}</h1>
          <p className="max-w-3xl text-sm leading-7 text-zinc-300 sm:text-base">{subtitle}</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-xs text-zinc-300">
          {getBuilderEditorLabel()}
        </div>
      </div>
    </header>
  );
}

export function BuilderMetricsRow({
  primaryMetricLabel = "Thiết bị đang kết nối",
  primaryMetricValue = "12",
  secondaryMetricLabel = "Cảnh báo hôm nay",
  secondaryMetricValue = "03",
  tertiaryMetricLabel = "Người dùng hoạt động",
  tertiaryMetricValue = "08",
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <StatTile label={primaryMetricLabel} value={primaryMetricValue} tone="emerald" />
      <StatTile label={secondaryMetricLabel} value={secondaryMetricValue} tone="sky" />
      <StatTile label={tertiaryMetricLabel} value={tertiaryMetricValue} tone="amber" />
    </div>
  );
}

export function BuilderOverviewPanel({
  eyebrow = "Builder Canvas",
  title = "Dashboard summary",
  description = "Các khối này có thể được kéo thả trong Builder để chỉnh trực quan phần giao diện dashboard.",
}) {
  return (
    <SectionCard eyebrow={eyebrow} title={title} description={description}>
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
          <BarChart3 className="h-5 w-5 text-emerald-300" />
          <div className="mt-3 text-lg font-semibold">Tổng quan</div>
          <p className="mt-1 text-sm text-zinc-300">Biểu đồ, số liệu và trạng thái theo thời gian thực.</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
          <Smartphone className="h-5 w-5 text-sky-300" />
          <div className="mt-3 text-lg font-semibold">Thiết bị</div>
          <p className="mt-1 text-sm text-zinc-300">Trạng thái online/offline, lần cuối xuất hiện và cảnh báo.</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
          <ShieldCheck className="h-5 w-5 text-amber-300" />
          <div className="mt-3 text-lg font-semibold">An toàn</div>
          <p className="mt-1 text-sm text-zinc-300">Preview mode chỉ hiển thị mock giao diện, không chạm vào token thật.</p>
        </div>
      </div>
    </SectionCard>
  );
}

export function BuilderSidePanel({
  eyebrow = "Editing Guard",
  title = "Bảo vệ logic thật",
  description = "An toàn cho preview, nghiêm ngặt trong production.",
  highlight = "Live auth logic is bypassed only while editing.",
  note = "Trong production, component thật vẫn dùng JWT, localStorage/sessionStorage và các request server như hiện tại.",
}) {
  return (
    <SectionCard eyebrow={eyebrow} title={title} description={description}>
      <div className="space-y-3 text-sm leading-6 text-zinc-300">
        <p>{highlight}</p>
        <p>{note}</p>
      </div>
    </SectionCard>
  );
}

export function BuilderSystemStrip({
  title = "Operational strip",
  leftLabel = "Alerts",
  leftValue = "3",
  centerLabel = "Screenshots",
  centerValue = "24",
  rightLabel = "Active rules",
  rightValue = "18",
}) {
  return (
    <SectionCard eyebrow="System status" title={title} description="Bộ khối phụ để Builder có thêm vùng kéo thả trong app shell.">
      <div className="grid gap-4 md:grid-cols-3">
        <StatTile label={leftLabel} value={leftValue} tone="rose" />
        <StatTile label={centerLabel} value={centerValue} tone="sky" />
        <StatTile label={rightLabel} value={rightValue} tone="emerald" />
      </div>
    </SectionCard>
  );
}

export function BuilderLoginPreview({ title = "Login gate", description = "Khối mô phỏng login để Builder có thể chỉnh giao diện đăng nhập, nhưng preview vẫn ưu tiên dashboard khi cần." }) {
  return (
    <SectionCard eyebrow="Auth" title={title} description={description}>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
          <div className="text-sm font-semibold">Email</div>
          <div className="mt-2 rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm text-zinc-300">parent@example.com</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
          <div className="text-sm font-semibold">Password</div>
          <div className="mt-2 rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm text-zinc-300">••••••••</div>
        </div>
      </div>
    </SectionCard>
  );
}

export function BuilderActivityPanel({ title = "Live activity", subtitle = "Một vài khối UI đại diện cho toàn bộ dashboard để Builder thao tác trực quan." }) {
  return (
    <SectionCard eyebrow="Activity" title={title} description={subtitle}>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
          <BellRing className="h-5 w-5 text-rose-300" />
          <div className="mt-3 text-sm font-semibold">Cảnh báo gần đây</div>
          <p className="mt-1 text-sm text-zinc-300">Khối này đại diện cho alert feed, log và trạng thái real-time.</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
          <Users className="h-5 w-5 text-sky-300" />
          <div className="mt-3 text-sm font-semibold">Người dùng & quyền</div>
          <p className="mt-1 text-sm text-zinc-300">Khối này đại diện cho RBAC, sub-account và permissions.</p>
        </div>
      </div>
    </SectionCard>
  );
}

export function AdminDashboardPreview() {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#183b2b_0%,_#08130f_45%,_#020403_100%)] text-white">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <BuilderTopBanner />
        <BuilderLoginPreview />
        <BuilderMetricsRow />
        <BuilderActivityPanel />
        <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
          <BuilderOverviewPanel />
          <BuilderSidePanel />
        </div>
        <BuilderSystemStrip />
      </div>
    </div>
  );
}

export function registerBuilderDashboardComponents() {
  if (typeof window === "undefined") return;

  Builder.registerComponent(BuilderTopBanner, {
    name: "Builder Top Banner",
    group: "Admin Dashboard",
    inputs: [
      { name: "heading", type: "text", defaultValue: "Admin Dashboard" },
      { name: "subtitle", type: "textarea", defaultValue: "Builder Preview Mode đã bật. Bạn có thể đổi chữ, màu và bố cục mà không đụng vào luồng xác thực thật." },
      { name: "badge", type: "text", defaultValue: "Builder Preview Mode" },
    ],
  });

  Builder.registerComponent(BuilderLoginPreview, {
    name: "Builder Login Preview",
    group: "Admin Dashboard",
    inputs: [
      { name: "title", type: "text", defaultValue: "Login gate" },
      { name: "description", type: "textarea", defaultValue: "Khối mô phỏng login để Builder có thể chỉnh giao diện đăng nhập, nhưng preview vẫn ưu tiên dashboard khi cần." },
    ],
  });

  Builder.registerComponent(BuilderMetricsRow, {
    name: "Builder Metrics Row",
    group: "Admin Dashboard",
    inputs: [
      { name: "primaryMetricLabel", type: "text", defaultValue: "Thiết bị đang kết nối" },
      { name: "primaryMetricValue", type: "text", defaultValue: "12" },
      { name: "secondaryMetricLabel", type: "text", defaultValue: "Cảnh báo hôm nay" },
      { name: "secondaryMetricValue", type: "text", defaultValue: "03" },
      { name: "tertiaryMetricLabel", type: "text", defaultValue: "Người dùng hoạt động" },
      { name: "tertiaryMetricValue", type: "text", defaultValue: "08" },
    ],
  });

  Builder.registerComponent(BuilderActivityPanel, {
    name: "Builder Activity Panel",
    group: "Admin Dashboard",
    inputs: [
      { name: "title", type: "text", defaultValue: "Live activity" },
      { name: "subtitle", type: "textarea", defaultValue: "Một vài khối UI đại diện cho toàn bộ dashboard để Builder thao tác trực quan." },
    ],
  });

  Builder.registerComponent(BuilderOverviewPanel, {
    name: "Builder Overview Panel",
    group: "Admin Dashboard",
    inputs: [
      { name: "eyebrow", type: "text", defaultValue: "Builder Canvas" },
      { name: "title", type: "text", defaultValue: "Dashboard summary" },
      { name: "description", type: "textarea", defaultValue: "Các khối này có thể được kéo thả trong Builder để chỉnh trực quan phần giao diện dashboard." },
    ],
  });

  Builder.registerComponent(BuilderSidePanel, {
    name: "Builder Side Panel",
    group: "Admin Dashboard",
    inputs: [
      { name: "eyebrow", type: "text", defaultValue: "Editing Guard" },
      { name: "title", type: "text", defaultValue: "Bảo vệ logic thật" },
      { name: "description", type: "textarea", defaultValue: "An toàn cho preview, nghiêm ngặt trong production." },
      { name: "highlight", type: "textarea", defaultValue: "Live auth logic is bypassed only while editing." },
      { name: "note", type: "textarea", defaultValue: "Trong production, component thật vẫn dùng JWT, localStorage/sessionStorage và các request server như hiện tại." },
    ],
  });

  Builder.registerComponent(BuilderSystemStrip, {
    name: "Builder System Strip",
    group: "Admin Dashboard",
    inputs: [
      { name: "title", type: "text", defaultValue: "Operational strip" },
      { name: "leftLabel", type: "text", defaultValue: "Alerts" },
      { name: "leftValue", type: "text", defaultValue: "3" },
      { name: "centerLabel", type: "text", defaultValue: "Screenshots" },
      { name: "centerValue", type: "text", defaultValue: "24" },
      { name: "rightLabel", type: "text", defaultValue: "Active rules" },
      { name: "rightValue", type: "text", defaultValue: "18" },
    ],
  });

  Builder.registerComponent(AdminDashboardPreview, {
    name: "Admin Dashboard Shell",
    group: "Admin Dashboard",
    description: "Editable dashboard shell for Builder preview mode.",
    inputs: [],
  });
}
