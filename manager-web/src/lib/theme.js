/**
 * CENTRALIZED THEME DESIGN SYSTEM TOKENS
 * Parental Control Manager Web UI v2.0
 * 
 * Strict palette rule:
 * - Emerald Ink (#064E3B)
 * - Champagne (#F8E7C9)
 * 
 * Usage in components:
 * const styles = getThemeStyles(theme);
 * <div className={styles.card}>
 *   <h3 className={styles.textBold}>Title</h3>
 *   <button className={styles.buttonPrimary}>Action</button>
 * </div>
 */

export const THEME_CONFIG = {
  fontFamily: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  colors: {
    navy: "#0E3746",
    cream: "#F4F2EC",
    beige: "#EAE8DC",
    crimson: "#BE2623",
    darkObsidian: "#09090b",
    darkCard: "#18181b",
    darkBorder: "#27272a",
  },
  light: {
    background: "bg-[#F4F2EC] text-[#0E3746]",
    card: "bg-[#EAE8DC] border-[#0E3746]/20 shadow-sm",
    cardCallout: "bg-[#0E3746] border-[#0E3746] text-[#F4F2EC]",
    text: "text-[#0E3746]",
    textMuted: "text-[#0E3746] opacity-90 font-medium",
    textBold: "text-[#0E3746] font-extrabold",
    buttonPrimary: "bg-[#0E3746] text-[#F4F2EC] hover:opacity-90 shadow-sm active:scale-[0.98]",
    buttonSecondary: "bg-[#EAE8DC] text-[#0E3746] hover:bg-[#F4F2EC] border border-[#0E3746]/20 active:scale-[0.98]",
    buttonDanger: "bg-[#BE2623] hover:bg-[#9a1e1b] border border-[#BE2623]/60 text-[#F4F2EC] active:scale-[0.98]",
    buttonSuccess: "bg-[#0E3746] hover:bg-[#0c2f3d] border border-[#0E3746]/60 text-[#F4F2EC] active:scale-[0.98]",
    input: "bg-[#F4F2EC] border-[#0E3746]/20 text-[#0E3746] placeholder-[#0E3746]/60 focus:border-[#0E3746]",
    badge: "bg-[#0E3746] text-[#F4F2EC] font-bold",
    badgeMuted: "bg-[#0E3746]/10 text-[#0E3746] border border-[#0E3746]/20 font-bold",
    header: "bg-[#F4F2EC]/95 border-[#0E3746]/20",
    navActive: "bg-[#0E3746] text-[#F4F2EC] shadow-md",
    navInactive: "text-[#0E3746] hover:bg-[#EAE8DC]",
  },
  dark: {
    background: "bg-zinc-950 text-zinc-100",
    card: "bg-zinc-900 border-zinc-800 shadow-sm",
    cardCallout: "bg-zinc-800 border-zinc-700 text-zinc-100",
    text: "text-zinc-100",
    textMuted: "text-zinc-400 font-medium",
    textBold: "text-zinc-100 font-extrabold",
    buttonPrimary: "bg-zinc-100 text-zinc-900 hover:bg-zinc-200 shadow-sm active:scale-[0.98]",
    buttonSecondary: "bg-zinc-800 text-zinc-100 hover:bg-zinc-700 border border-zinc-700 active:scale-[0.98]",
    buttonDanger: "bg-rose-900/50 hover:bg-rose-900 border border-rose-800 text-rose-100 active:scale-[0.98]",
    buttonSuccess: "bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-100 active:scale-[0.98]",
    input: "bg-zinc-950 border-zinc-800 text-zinc-100 placeholder-zinc-500 focus:border-zinc-500",
    badge: "bg-zinc-800 text-zinc-100 font-bold",
    badgeMuted: "bg-zinc-900 text-zinc-400 border border-zinc-800 font-bold",
    header: "bg-zinc-950/95 border-zinc-800",
    navActive: "bg-zinc-100 text-zinc-900 shadow-md",
    navInactive: "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900",
  }
};

/**
 * Returns theme styles based on current theme mode ('dark' | 'light')
 */
export function getThemeStyles(theme = "dark") {
  return theme === "dark" ? THEME_CONFIG.dark : THEME_CONFIG.light;
}
