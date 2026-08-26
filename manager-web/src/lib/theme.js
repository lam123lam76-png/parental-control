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
    emeraldInk: "#064E3B",
    champagne: "#F8E7C9",
    darkObsidian: "#09090b",
    darkCard: "#18181b",
    darkBorder: "#27272a",
    lightCard: "#FFFFFF",
    lightBorder: "#DECC9F",
  },
  light: {
    background: "bg-[#F8E7C9] text-[#064E3B]",
    card: "bg-[#FFFFFF] border-[#DECC9F] shadow-sm",
    cardCallout: "bg-[#064E3B] border-emerald-800 text-[#F8E7C9]",
    text: "text-[#064E3B]",
    textMuted: "text-[#064E3B] opacity-90 font-medium",
    textBold: "text-[#064E3B] font-extrabold",
    buttonPrimary: "bg-[#064E3B] text-[#F8E7C9] hover:opacity-90 shadow-sm active:scale-[0.98]",
    buttonSecondary: "bg-[#EEDCBA] text-[#064E3B] hover:bg-[#E5CF9F] active:scale-[0.98]",
    buttonDanger: "bg-[#3f121a] hover:bg-[#521722] border border-emerald-900/60 text-[#F8E7C9] active:scale-[0.98]",
    buttonSuccess: "bg-[#0e3325] hover:bg-[#154633] border border-emerald-800/60 text-[#F8E7C9] active:scale-[0.98]",
    input: "bg-[#FFFFFF] border-[#DECC9F] text-[#064E3B] placeholder-[#064E3B]/60 focus:border-[#064E3B]",
    badge: "bg-[#064E3B] text-[#F8E7C9] font-bold",
    badgeMuted: "bg-[#064E3B]/10 text-[#064E3B] border border-zinc-800 font-bold",
    header: "bg-[#F8E7C9]/95 border-[#DECC9F]",
    navActive: "bg-[#064E3B] text-[#F8E7C9] shadow-md",
    navInactive: "text-[#064E3B] hover:bg-[#EEDCBA]",
  },
  dark: {
    background: "bg-[#09090b] text-[#F8E7C9]",
    card: "bg-[#18181b] border-[#27272a] shadow-sm",
    cardCallout: "bg-[#064E3B] border-emerald-800 text-[#F8E7C9]",
    text: "text-[#F8E7C9]",
    textMuted: "text-[#F8E7C9]/85 font-medium",
    textBold: "text-[#F8E7C9] font-extrabold",
    buttonPrimary: "bg-[#064E3B] text-[#F8E7C9] hover:opacity-90 shadow-sm active:scale-[0.98]",
    buttonSecondary: "bg-[#27272a] text-[#F8E7C9] hover:bg-[#3f3f46] border border-[#27272a] hover:border-[#3f3f46] active:scale-[0.98]",
    buttonDanger: "bg-[#3f121a] hover:bg-[#521722] border border-emerald-900/60 text-[#F8E7C9] active:scale-[0.98]",
    buttonSuccess: "bg-[#0e3325] hover:bg-[#154633] border border-emerald-800/60 text-[#F8E7C9] active:scale-[0.98]",
    input: "bg-[#09090b] border-[#27272a] text-[#F8E7C9] placeholder-[#F8E7C9]/60 focus:border-[#064E3B]",
    badge: "bg-[#064E3B] text-[#F8E7C9] font-bold",
    badgeMuted: "bg-[#27272a] text-[#F8E7C9] border border-[#27272a] font-bold",
    header: "bg-[#09090b]/95 border-[#27272a]",
    navActive: "bg-[#064E3B] text-[#F8E7C9] shadow-md",
    navInactive: "text-[#F8E7C9]/80 hover:text-[#F8E7C9] hover:bg-[#18181b]",
  }
};

/**
 * Returns theme styles based on current theme mode ('dark' | 'light')
 */
export function getThemeStyles(theme = "dark") {
  return theme === "dark" ? THEME_CONFIG.dark : THEME_CONFIG.light;
}
