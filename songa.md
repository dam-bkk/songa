# Songa — Claude Code Build Prompt

> Copy everything below the line into Claude Code as your first message in a fresh session.
> Before pasting, `cd` into an empty folder where you want the project to live.

---

# Project: Songa — Computer Vision for African Basketball

You are helping me build **Songa**, a pitch-ready prototype for a computer vision platform that analyzes basketball games for coaches and academies in Côte d'Ivoire and across Africa. No real videos exist yet — this phase is about **brand identity, landing page, and product UI mockups** that look production-grade for investor and client pitches. The CV pipeline will be scaffolded but stubbed.

## Goals for this session

1. Set up a clean Next.js 14 (App Router) + TypeScript + Tailwind project
2. Build a polished bilingual (French default, English toggle) landing page
3. Build two product UI mockups: **Coach dashboard** and **Academy dashboard**
4. Establish brand identity: logo (SVG), color tokens, typography
5. Scaffold a `cv-pipeline/` folder with a Python stub ready for real videos later
6. Write a clean `README.md` and a `CLAUDE.md` so future sessions stay productive

## Brand identity — fixed decisions, do not re-debate

- **Name:** Songa
- **Tagline (FR):** _L'intelligence visuelle au service du jeu._
- **Tagline (EN):** _Visual intelligence for the game._
- **Origin line:** _Conçu en Côte d'Ivoire · Pour l'Afrique_ / _Built in Côte d'Ivoire · For Africa_
- **Aesthetic direction:** athletic precision meets editorial sophistication. Think Linear × Hudl × L'Équipe Magazine. Dark mode primary. Confident, premium, not flashy.
- **Color tokens (Tailwind config):**
  - `ink`: `#0E0D0B` (near-black, warm undertone — primary background)
  - `bone`: `#F2EDE3` (off-white paper — primary text on dark)
  - `court`: `#E8743C` (warm basketball orange — scarce accent only, max 5% of any view)
  - `signal`: `#7BE0A8` (electric mint — for "live" / active data states only)
  - `slate-900`: `#1A1815` (elevated surface)
  - `slate-700`: `#3A3631` (borders, dividers)
  - `slate-400`: `#9A9389` (muted text)
- **Typography:**
  - Display: **Fraunces** (Google Fonts) — for hero, section titles, big numbers. Use opsz 144, weight 400–500, soft 30, tight tracking.
  - Body: **Geist** (Google Fonts) — for paragraphs, UI, buttons. Weights 300/400/500.
  - Mono: **JetBrains Mono** — for stats, codes, timestamps, labels in the dashboards.
- **Logo:** wordmark "Songa" in Fraunces, with a small custom mark — a single curved trajectory line ending in a dot (the "trace" — symbol of CV tracking). Provide as `/public/logo.svg` and a wordmark-only variant.
- **Signature visual element:** the **trace** — animated curved SVG paths with stroke-dasharray reveal, used in hero, section dividers, and as overlay on dashboard mockups. This is the brand's visual DNA.

## Tech stack — use exactly these

- **Framework:** Next.js 14 with App Router and TypeScript (`create-next-app@latest` with --typescript --tailwind --app --eslint)
- **Styling:** Tailwind CSS with custom tokens (above) in `tailwind.config.ts`
- **Icons:** `lucide-react`
- **Animations:** `framer-motion`
- **i18n:** lightweight — a single React context (`LangProvider`) with two dictionaries (`fr.ts`, `en.ts`). No heavy i18n libraries. FR is default, toggle in header.
- **Charts/dashboards:** `recharts` for charts, custom SVG for court/heatmap visuals
- **Fonts:** Next.js `next/font/google` for Fraunces, Geist, JetBrains_Mono
- **Linting:** Keep ESLint + Prettier defaults; format on save

Do **not** install: any UI kit (shadcn is fine if needed for primitives only — Button, Dialog, Tabs), any analytics, any auth, any database. This is a pitch prototype.

## Project structure

```
songa/
├── app/
│   ├── layout.tsx              # Root layout, fonts, LangProvider
│   ├── page.tsx                # Landing page
│   ├── coach/page.tsx          # Coach dashboard mockup
│   ├── academy/page.tsx        # Academy dashboard mockup
│   └── globals.css
├── components/
│   ├── brand/
│   │   ├── Logo.tsx            # Full wordmark + mark
│   │   └── Wordmark.tsx        # Wordmark only
│   ├── landing/
│   │   ├── Header.tsx          # Sticky header, lang toggle
│   │   ├── Hero.tsx            # Hero with animated trace
│   │   ├── StatsBar.tsx        # 94% / <2min / 12 / 0
│   │   ├── Features.tsx        # 4 feature cards
│   │   ├── HowItWorks.tsx      # 3 steps
│   │   ├── Audience.tsx        # Coach + Academy split
│   │   ├── Footer.tsx
│   ├── dashboard/
│   │   ├── CoachDashboard.tsx
│   │   ├── AcademyDashboard.tsx
│   │   ├── CourtHeatmap.tsx    # SVG basketball court with shot zones
│   │   ├── PlayerTable.tsx
│   │   ├── StatCard.tsx
│   │   ├── TrajectoryOverlay.tsx  # The animated trace, reusable
│   ├── ui/                     # Small primitives: Button, Tag, etc.
├── lib/
│   ├── i18n/
│   │   ├── fr.ts
│   │   ├── en.ts
│   │   └── LangProvider.tsx
│   └── mockData.ts             # Fake game/player data for dashboards
├── public/
│   ├── logo.svg
│   └── wordmark.svg
├── cv-pipeline/                # Python stub, separate from web app
│   ├── README.md               # How to set up Python env when videos arrive
│   ├── requirements.txt        # ultralytics, opencv-python, numpy, etc.
│   ├── analyze.py              # Stub: takes video path, prints "TODO"
│   └── .gitignore              # ignore venv, weights, sample videos
├── tailwind.config.ts
├── tsconfig.json
├── package.json
├── README.md                   # Project overview, run instructions
└── CLAUDE.md                   # Persistent context for future Claude Code sessions
```

## Page-by-page specs

### Landing page (`app/page.tsx`)

**Header (sticky, blurred bg on scroll):**

- Logo on left
- Nav (centered desktop, hidden mobile): Produit / Solutions / À propos
- Right: language toggle (FR | EN), "Connexion" link, primary CTA button "Demander une démo" (court orange)

**Hero:**

- Two-column on desktop (60/40), stacked on mobile
- Left: small uppercase mono eyebrow ("Vision par ordinateur · Basketball africain"), giant Fraunces headline with a line break, body sub, two CTAs (primary court-orange, secondary ghost), small footer line "Conçu en Côte d'Ivoire · Pour l'Afrique" with a tiny location pin
- Right: a stylized SVG of a basketball half-court (top-down view) with **animated trace lines** showing player trajectories and a ball arc landing in the basket. Use stroke-dasharray + framer-motion for the reveal. Add 4–5 small pulsing dots representing tracked players. This is the hero's wow moment — make it elegant, not busy.

**Stats bar (full-width, ink bg, top + bottom hairline borders in slate-700):**

- 4 columns: 94% / <2min / 12 / 0
- Big Fraunces numbers, small mono labels below, separated by thin vertical dividers
- Subtle staggered float-up animation on scroll-in

**Features section:**

- 4 cards in 2×2 grid (1 col mobile)
- Each card: icon (lucide), title (Fraunces), description (Geist)
- Cards have subtle border (slate-700), slate-900 bg, hover lift

**How it works:**

- 3 steps in horizontal layout (vertical mobile)
- Big mono numbers (01/02/03), title, description
- Connecting trace line between steps (decorative SVG)

**Audience split:**

- Two large cards side-by-side: Entraîneurs / Académies & Clubs
- Each links to its respective dashboard mockup (`/coach`, `/academy`)
- Hover: subtle court-orange border accent + arrow animation

**Footer:**

- Wordmark, tagline, 3 columns of links (placeholder — Produit / Entreprise / Légal)
- Bottom: "© 2026 Songa · Conçu à Abidjan" + lang toggle mirror

### Coach dashboard (`app/coach/page.tsx`)

Mockup with realistic-looking but fake data. Layout:

- Top bar: "← Retour", title "Tableau de bord — Match", subtitle "ABC Fighters vs Étoile Filante du Sahel · 14 nov. 2026", export button
- 4 stat cards row: Score 78–72 / Possessions 94 / Efficacité off. 108.4 / Rebonds 42
- Main grid (2 cols):
  - Left: video placeholder card with play button + scrubber + "trace" overlay illustration
  - Right: shot chart (SVG basketball court with colored zones — heatmap of shots)
- Below: PlayerTable — rows of players with mini-stats (PTS, REB, AST, +/-) and a tiny sparkline per player
- Bottom: "Actions clés détectées" — timeline of detected events (steal, dunk, 3-pointer, etc.) with timestamps

### Academy dashboard (`app/academy/page.tsx`)

- Top bar: title "Tableau de bord — Académie", subtitle "Centre de Formation Songa · Saison 2025–26"
- 4 stat cards: Joueurs suivis 47 / Matchs analysés 128 / Heures capturées 1240h / Talents émergents 6
- Main: roster grid (cards of players with photo placeholder, name, age category, key stat trend)
- "Progression collective" line chart (recharts) — team metric evolution over season
- "Talents émergents" highlighted section — top 3 AI-flagged players with reason ("+18% efficacité ce mois")

## Interaction & motion guidelines

- **Page load:** staggered float-up on hero elements (delays: 0ms, 100ms, 200ms, 300ms)
- **Hero trace:** 3-second reveal on mount, then idle subtle pulse on dots
- **Scroll reveals:** use framer-motion `whileInView` for sections, threshold 0.2
- **Hover states:** all interactive elements get a 150ms transition
- **No purple gradients. No glassmorphism. No emoji in UI.** Editorial restraint.

## i18n implementation

- `lib/i18n/fr.ts` and `en.ts` export typed dictionaries with the same shape
- `LangProvider` stores current lang in React state + localStorage
- `useT()` hook returns the current dictionary
- Default to `fr`. Toggle in header switches instantly with no page reload.

## CV pipeline stub (`cv-pipeline/`)

Don't implement real CV. Just:

**`requirements.txt`:**

```
ultralytics>=8.3.0
opencv-python>=4.10.0
numpy>=1.26.0
torch>=2.4.0
torchvision>=0.19.0
supervision>=0.24.0
pandas>=2.2.0
```

**`analyze.py`:** a stub that accepts `--video PATH`, prints "Songa CV pipeline — stub. Real implementation coming when videos arrive.", and outlines (in comments) the planned pipeline: detection → tracking → ball trajectory → action classification → stats export.

**`README.md` (in cv-pipeline/):** explains how to set up a Python venv, install requirements, expected video formats (1080p MP4, 30fps), folder structure for sample videos, target hardware (CUDA-capable GPU for production, CPU okay for dev).

## CLAUDE.md (root)

Write a concise `CLAUDE.md` with:

- Project description (1 paragraph)
- Tech stack (bullet list)
- Brand tokens (colors + fonts, copy from above)
- Folder structure (tree)
- Run commands (`npm run dev`, etc.)
- Conventions: bilingual, FR default, no purple, no emoji in UI, editorial restraint
- "When adding new pages, always update both fr.ts and en.ts dictionaries"
- "CV pipeline lives in `cv-pipeline/` and is intentionally separate from the web app"

## Quality bar

This is a **pitch-ready** prototype. The bar is: when an investor or a federation director opens this on their laptop, they should think _"this is a real, well-funded product."_ That means:

- Real-feeling typography (Fraunces on hero is non-negotiable)
- Real-feeling data (no "Lorem ipsum", no "Player 1, Player 2" — use plausible Ivorian/West African names like Yao Konaté, Aboubacar Diabaté, Fatim Coulibaly, etc.)
- Smooth animations that feel intentional, not decorative
- Mobile-responsive (test at 375px, 768px, 1280px, 1920px)
- No console errors, no layout shift, fonts loaded properly

## Execution order — follow exactly

1. Run `npx create-next-app@latest songa --typescript --tailwind --app --eslint --src-dir=false --import-alias="@/*"` and `cd songa`
2. Install deps: `npm i lucide-react framer-motion recharts`
3. Configure `tailwind.config.ts` with brand tokens
4. Set up `next/font` for Fraunces, Geist, JetBrains Mono in `app/layout.tsx`
5. Build the i18n layer (`lib/i18n/`)
6. Build brand components (`Logo.tsx`, `Wordmark.tsx`)
7. Build the landing page section by section, in order: Header → Hero → StatsBar → Features → HowItWorks → Audience → Footer
8. Build CoachDashboard
9. Build AcademyDashboard
10. Scaffold `cv-pipeline/`
11. Write `README.md` and `CLAUDE.md`
12. Run `npm run dev`, verify no errors, screenshot key views

## Confirm before starting

Before you write any code, reply with:

1. A 5-bullet summary of what you understood
2. Any clarifying question (max 3, only if truly blocking)
3. The exact `create-next-app` command you'll run

Then wait for my "go."
