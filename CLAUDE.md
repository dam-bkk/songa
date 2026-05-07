# Songa — Computer Vision for African Basketball

## Project overview
Songa is a pitch-ready SaaS landing page + demo dashboards for a computer vision platform targeting basketball coaches and academies across Africa. Built in Côte d'Ivoire concept.

## Stack
- Next.js 16 (App Router) + TypeScript
- Tailwind CSS v4 (CSS-based config via `@theme` in globals.css — no tailwind.config.ts)
- Framer Motion (animations)
- Recharts (academy progression chart)
- Lucide React (icons)
- next/font/google (Fraunces, Geist, JetBrains Mono)

## Brand tokens (defined in app/globals.css @theme)
- `ink` = #0E0D0B (background)
- `bone` = #F2EDE3 (foreground)
- `court` = #E8743C (primary accent — orange)
- `signal` = #7BE0A8 (positive/green accent)
- `slate-900` = #1A1815 (card background)
- `slate-700` = #3A3631 (borders)
- `slate-400` = #9A9389 (muted text)

## Font variables
CSS vars injected by Next.js layout:
- `--font-fraunces-var` → serif display font
- `--font-geist-var` → sans body font
- `--font-jetbrains-var` → monospace/data font

Tailwind utilities: `font-fraunces`, `font-geist`, `font-mono`

## Routes
- `/` — Marketing landing page (Header, Hero, StatsBar, Features, HowItWorks, Audience, Footer)
- `/coach` — Coach match dashboard (StatCard, CourtHeatmap, PlayerTable, EventTimeline)
- `/academy` — Academy dashboard (StatCard, Recharts LineChart, player roster cards, emerging talents)

## Key patterns
- i18n: `lib/i18n.tsx` — LangProvider/useLang hook, FR default, FR/EN toggle
- Theme: `lib/theme.tsx` — ThemeProvider/useTheme, dark default, localStorage "songa-theme"
- Mock data: `lib/mockData.ts` — players, academyPlayers, progressionData, events, shotZones

## No emojis as UI elements
Use SVG or CSS shapes only. Lucide icons are fine.

## Tailwind v4 note
This project uses Tailwind v4. Custom colors/fonts are defined in `app/globals.css` using `@theme {}` blocks, NOT in a tailwind.config.ts file.
