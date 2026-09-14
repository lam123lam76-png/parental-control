---
name: Parental Control Manager Web
colors:
  emerald-ink: "#064E3B"
  champagne: "#F8E7C9"
  dark-obsidian: "#09090b"
  dark-card: "#18181b"
  dark-border: "#27272a"
  light-card: "#FFFFFF"
  light-border: "#DECC9F"
  danger-dark: "#3f121a"
  danger-light: "#521722"
  success-dark: "#0e3325"
  success-light: "#154633"
  primary: "{colors.emerald-ink}"
  secondary: "{colors.champagne}"
  background-light: "{colors.champagne}"
  background-dark: "{colors.dark-obsidian}"
typography:
  body:
    fontFamily: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif
    fontSize: 1rem
rounded:
  sm: 4px
  md: 8px
  lg: 12px
spacing:
  sm: 8px
  md: 16px
  lg: 24px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.secondary}"
    rounded: "{rounded.sm}"
  button-secondary:
    backgroundColor: "#EEDCBA"
    textColor: "{colors.primary}"
    rounded: "{rounded.sm}"
  button-danger:
    backgroundColor: "{colors.danger-dark}"
    textColor: "{colors.secondary}"
    rounded: "{rounded.sm}"
  button-success:
    backgroundColor: "{colors.success-dark}"
    textColor: "{colors.secondary}"
    rounded: "{rounded.sm}"
  card-light:
    backgroundColor: "{colors.light-card}"
    rounded: "{rounded.lg}"
---

## Overview

Parental Control Manager Web UI v2.0 focuses on a centralized design system. The UI evokes a safe, clear, and secure environment.

## Colors

The palette relies on a strict dual-tone base: Emerald Ink and Champagne, augmented by necessary functional colors (danger, success) and dark mode neutrals.

- **Emerald Ink (#064E3B):** Primary action color, bold text in light mode, primary buttons.
- **Champagne (#F8E7C9):** Main background for light mode, primary text for dark mode.
- **Dark Obsidian (#09090b):** Main background for dark mode.
- **Danger (#3f121a):** Used for destructive actions (e.g., Lock Device).
- **Success (#0e3325):** Used for positive actions (e.g., Unlock Device).

## Typography

Standard sans-serif stack ensuring maximum legibility across all platforms (Windows, macOS, iOS, Android).

## Shapes

Card containers typically use soft rounded corners (`md` or `lg`), buttons use `sm` or `md`.

## Layout

A Top Header Navigation, Left Sidebar Navigation, and Mobile Bottom Navigation Bar construct the core layout.

## Components

Buttons and cards must strictly follow the tokenized color guidelines instead of ad-hoc Tailwind utility classes.
