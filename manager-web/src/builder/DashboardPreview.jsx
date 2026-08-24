import React from "react";
import { Builder } from "@builder.io/react";
import { BarChart3, ShieldCheck, Smartphone, Sparkles } from "lucide-react";
import { getBuilderEditorLabel } from "./mode";

function StatTile({ label, value, tone = "emerald" }) {
  const tones = {
    emerald: "border-emerald-400/30 bg-emerald-400/10 text-emerald-100",
    amber: "border-amber-400/30 bg-amber-400/10 text-amber-100",
    sky: "border-sky-400/30 bg-sky-400/10 text-sky-100",
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

export function AdminDashboardPreview({
  heading = "Admin Dashboard",
  subtitle = "Builder Preview Mode đã bật. Bạn có thể đổi chữ, màu và bố cục mà không đụng vào luồng xác thực thật.",
  highlight = "Live auth logic is bypassed only while editing.",
  primaryMetricLabel = "Thiết bị đang kết nối",
  primaryMetricValue = "12",
  secondaryMetricLabel = "Cảnh báo hôm nay",
  secondaryMetricValue = "03",
  accentNote = "An toàn cho preview, nghiêm ngặt trong production.",
}) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#183b2b_0%,_#08130f_45%,_#020403_100%)] text-white">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <header className="rounded-[32px] border border-white/10 bg-black/30 p-6 shadow-2xl backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-3 max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-[11px] uppercase tracking-[0.24em] text-emerald-100">
                <Sparkles className="h-3.5 w-3.5" />
                {getBuilderEditorLabel()}
              </div>
              <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">{heading}</h1>
              <p className="max-w-3xl text-sm leading-7 text-zinc-300 sm:text-base">{subtitle}</p>
            </div>
            <div className="grid gap-3 sm:min-w-72 sm:grid-cols-2">
              <StatTile label={primaryMetricLabel} value={primaryMetricValue} tone="emerald" />
              <StatTile label={secondaryMetricLabel} value={secondaryMetricValue} tone="sky" />
            </div>
          </div>
        </header>

        <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
          <SectionCard
            eyebrow="Builder Canvas"
            title="Dashboard summary"
            description="Các khối này có thể được kéo thả trong Builder để chỉnh trực quan phần giao diện dashboard."
          >
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

          <SectionCard
            eyebrow="Editing Guard"
            title="Bảo vệ logic thật"
            description={accentNote}
          >
            <div className="space-y-3 text-sm leading-6 text-zinc-300">
              <p>{highlight}</p>
              <p>Trong production, component thật vẫn dùng JWT, localStorage/sessionStorage và các request server như hiện tại.</p>
            </div>
          </SectionCard>
        </div>
      </div>
    </div>
  );
}

if (typeof window !== "undefined") {
  Builder.registerComponent(AdminDashboardPreview, {
    name: "Admin Dashboard",
    description: "Editable dashboard shell for Builder preview mode.",
    inputs: [
      { name: "heading", type: "text", defaultValue: "Admin Dashboard" },
      {
        name: "subtitle",
        type: "textarea",
        defaultValue:
          "Builder Preview Mode đã bật. Bạn có thể đổi chữ, màu và bố cục mà không đụng vào luồng xác thực thật.",
      },
      {
        name: "highlight",
        type: "textarea",
        defaultValue: "Live auth logic is bypassed only while editing.",
      },
      { name: "primaryMetricLabel", type: "text", defaultValue: "Thiết bị đang kết nối" },
      { name: "primaryMetricValue", type: "text", defaultValue: "12" },
      { name: "secondaryMetricLabel", type: "text", defaultValue: "Cảnh báo hôm nay" },
      { name: "secondaryMetricValue", type: "text", defaultValue: "03" },
      {
        name: "accentNote",
        type: "textarea",
        defaultValue: "An toàn cho preview, nghiêm ngặt trong production.",
      },
    ],
  });
}

