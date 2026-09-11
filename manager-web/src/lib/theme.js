/**
 * CENTRALIZED THEME DESIGN SYSTEM TOKENS
 * Parental Control Manager Web UI v2.0
 *
 * Palette:
 * - Navy Ink  (#0E3746)
 * - Cream     (#F4F2EC)
 * - Beige     (#EAE8DC)
 * - Crimson   (#BE2623)
 *
 * SHAPE RULE (single source of truth):
 *   Every "shape" (card, chip, row, badge, button) is expressed with a SHADOW,
 *   never with a 1px line border. Do not add `border` to card-like elements —
 *   use the tokens below so the whole UI stays consistent.
 *
 * Usage:
 *   const styles = getThemeStyles(theme);
 *   <div className={`rounded-xl ${styles.card}`}>
 */

export const THEME_CONFIG = {
  fontFamily: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  colors: {
    navy: "#0E3746",
    cream: "#F4F2EC",
    beige: "#EAE8DC",
    crimson: "#BE2623",
    online: "#22c55e",   // leaf green — device ONLINE
    offline: "#f43f5e",  // rose — device OFFLINE
    darkObsidian: "#09090b",
    darkCard: "#18181b",
    darkBorder: "#27272a",
  },
  light: {
    background: "bg-[#F4F2EC] text-[#0E3746]",

    /* --- SHAPES: shadow only, no line borders --- */
    card: "bg-[#EAE8DC] shadow-[0_2px_10px_rgba(14,55,70,0.10)]",
    cardCallout: "bg-[#0E3746] text-[#F4F2EC] shadow-[0_3px_14px_rgba(14,55,70,0.28)]",
    chip: "bg-[#EAE8DC] text-[#0E3746] shadow-[0_1px_4px_rgba(14,55,70,0.12)]",
    chipActive: "bg-[#0E3746] text-[#F4F2EC] shadow-[0_2px_8px_rgba(14,55,70,0.35)]",
    row: "bg-[#F4F2EC] text-[#0E3746] shadow-[0_1px_4px_rgba(14,55,70,0.10)]",
    rowHover: "hover:shadow-[0_3px_10px_rgba(14,55,70,0.18)]",
    rowSelected: "bg-[#0E3746]/15 text-[#0E3746] shadow-[0_2px_8px_rgba(14,55,70,0.20)]",
    inset: "bg-[#F4F2EC] shadow-[inset_0_1px_3px_rgba(14,55,70,0.10)]",

    /* --- TEXT --- */
    text: "text-[#0E3746]",
    textMuted: "text-[#0E3746] opacity-80 font-medium",
    textBold: "text-[#0E3746] font-extrabold",
    metricLabel: "text-[#0E3746] opacity-75 font-bold",
    metricValue: "text-[#0E3746] font-extrabold",

    /* --- BUTTONS: shadow, no line borders --- */
    buttonPrimary: "bg-[#0E3746] text-[#F4F2EC] hover:opacity-90 shadow-[0_2px_8px_rgba(14,55,70,0.30)] active:scale-[0.98]",
    buttonSecondary: "bg-[#EAE8DC] text-[#0E3746] hover:bg-[#F4F2EC] shadow-[0_1px_4px_rgba(14,55,70,0.12)] active:scale-[0.98]",
    buttonDanger: "bg-[#BE2623] hover:bg-[#9a1e1b] text-[#F4F2EC] shadow-[0_2px_8px_rgba(190,38,35,0.35)] active:scale-[0.98]",
    buttonSuccess: "bg-[#0E3746] hover:bg-[#0c2f3d] text-[#F4F2EC] shadow-[0_2px_8px_rgba(14,55,70,0.30)] active:scale-[0.98]",

    /* Inputs keep a soft outline (affordance), still no hard 1px line look. */
    input: "bg-[#F4F2EC] border border-[#0E3746]/20 text-[#0E3746] placeholder-[#0E3746]/60 focus:border-[#0E3746] shadow-[inset_0_1px_2px_rgba(14,55,70,0.06)]",

    badge: "bg-[#0E3746] text-[#F4F2EC] font-bold shadow-[0_1px_4px_rgba(14,55,70,0.25)]",
    badgeMuted: "bg-[#0E3746]/10 text-[#0E3746] font-bold shadow-[0_1px_3px_rgba(14,55,70,0.10)]",

    header: "bg-[#F4F2EC]/95 shadow-[0_1px_6px_rgba(14,55,70,0.10)]",
    navActive: "bg-[#0E3746] text-[#F4F2EC] shadow-[0_2px_8px_rgba(14,55,70,0.30)]",
    navInactive: "text-[#0E3746] hover:bg-[#EAE8DC]",

    /* Status colours — ONLINE is leaf green, OFFLINE is rose. */
    statusOnline: "bg-emerald-500",
    statusOffline: "bg-rose-500",
    statusOnlineText: "text-emerald-600",
    statusOfflineText: "text-rose-500",
  },
  dark: {
    background: "bg-zinc-950 text-zinc-100",

    /* --- SHAPES: shadow only, no line borders --- */
    card: "bg-zinc-900 shadow-lg shadow-black/40",
    cardCallout: "bg-zinc-800 text-zinc-100 shadow-lg shadow-black/50",
    chip: "bg-zinc-800 text-zinc-300 shadow-[0_1px_4px_rgba(0,0,0,0.45)]",
    chipActive: "bg-zinc-100 text-zinc-900 shadow-[0_2px_8px_rgba(0,0,0,0.55)]",
    row: "bg-zinc-900 text-zinc-200 shadow-[0_1px_4px_rgba(0,0,0,0.40)]",
    rowHover: "hover:shadow-[0_3px_10px_rgba(0,0,0,0.60)]",
    rowSelected: "bg-zinc-800 text-zinc-100 shadow-[0_2px_8px_rgba(0,0,0,0.55)]",
    inset: "bg-zinc-950 shadow-[inset_0_1px_3px_rgba(0,0,0,0.50)]",

    /* --- TEXT --- */
    text: "text-zinc-100",
    textMuted: "text-zinc-400 font-medium",
    textBold: "text-zinc-100 font-extrabold",
    metricLabel: "text-zinc-400 font-bold",
    metricValue: "text-zinc-100 font-extrabold",

    /* --- BUTTONS --- */
    buttonPrimary: "bg-zinc-100 text-zinc-900 hover:bg-zinc-200 shadow-[0_2px_8px_rgba(0,0,0,0.45)] active:scale-[0.98]",
    buttonSecondary: "bg-zinc-800 text-zinc-100 hover:bg-zinc-700 shadow-[0_1px_4px_rgba(0,0,0,0.45)] active:scale-[0.98]",
    buttonDanger: "bg-rose-900/50 hover:bg-rose-900 text-rose-100 shadow-[0_2px_8px_rgba(0,0,0,0.45)] active:scale-[0.98]",
    buttonSuccess: "bg-zinc-800 hover:bg-zinc-700 text-zinc-100 shadow-[0_2px_8px_rgba(0,0,0,0.45)] active:scale-[0.98]",

    input: "bg-zinc-950 border border-zinc-800 text-zinc-100 placeholder-zinc-500 focus:border-zinc-500 shadow-[inset_0_1px_2px_rgba(0,0,0,0.35)]",

    badge: "bg-zinc-800 text-zinc-100 font-bold shadow-[0_1px_4px_rgba(0,0,0,0.40)]",
    badgeMuted: "bg-zinc-900 text-zinc-400 font-bold shadow-[0_1px_3px_rgba(0,0,0,0.35)]",

    header: "bg-zinc-950/95 shadow-[0_1px_6px_rgba(0,0,0,0.50)]",
    navActive: "bg-zinc-100 text-zinc-900 shadow-[0_2px_8px_rgba(0,0,0,0.50)]",
    navInactive: "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900",

    /* Status colours — same semantic colours in dark mode. */
    statusOnline: "bg-emerald-500",
    statusOffline: "bg-rose-500",
    statusOnlineText: "text-emerald-400",
    statusOfflineText: "text-rose-400",
  }
};

/**
 * Returns theme styles based on current theme mode ('dark' | 'light')
 */
export function getThemeStyles(theme = "dark") {
  return theme === "dark" ? THEME_CONFIG.dark : THEME_CONFIG.light;
}
