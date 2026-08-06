# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed
- Removed a hardcoded placeholder GitHub URL
  (`github.com/pinesprout/pinesprout` — not a real repo) that the
  "Built with PineSprout" app footer and every generated README's
  "Generated with PineSprout" line linked to. Both are now plain,
  unlinked text. `pyproject.toml`'s project URLs and the README's own
  badges/clone command now point at the actual repo
  (`github.com/85599/pinesprout`) instead.

### Fixed
- Two real bugs caught only by taking actual browser screenshots
  (invisible to exception-only automated tests):
  - The white "X / Twitter" button on the About page had invisible text
    (white-on-white) — the color-inherit CSS override only targeted `p`
    and `div` descendants, but Streamlit renders button labels in a
    `span`. Fixed by targeting `*` (every descendant) instead.
  - Toggling the theme reset the sidebar's mode selection back to the
    first option ("Describe my strategy") every time, losing whatever
    page you were on. Caused by an unnecessary manual `st.rerun()` in
    `theme_toggle()` that truncated the script pass before the mode
    radio was re-declared, and Streamlit garbage-collects state for
    widgets skipped in a pass. Removed the redundant rerun (Streamlit
    already reruns automatically on widget change) and reordered
    `inject_theme_css()` to run immediately after the toggle so the new
    theme's CSS is applied in the same pass instead of lagging a click
    behind.
- Added `docs/screenshots/` with real captures of every mode plus the
  light theme, embedded in the README.

### Added
- Overview tab for NSE Index Watch: bar chart (% change by index) and
  sentiment pie chart via `plotly` (optional — degrades to a plain
  table if not installed), a searchable/filterable data table, and a
  CSV download button.
- Optional hands-free auto-refresh (`streamlit-autorefresh`, optional —
  falls back to the manual refresh button if not installed): Off / 30s /
  1min / 2min / 5min.
- API key input now also appears directly in the AI-generate mode's
  main panel (in addition to the sidebar), so it's impossible to miss
  even without scrolling the sidebar.

### Fixed
- Removed `NIFTYPVTBANK.NS` from the Index Watch — it was an unverified
  ticker that turned out to be delisted/unavailable on Yahoo Finance,
  spamming the console with retry warnings on every refresh. Replaced
  with `^CNXCONSUM` (NIFTY CONSUMPTION), and every remaining Index Watch
  ticker has now been individually verified against Yahoo Finance's own
  listing pages.
- Silenced yfinance's per-attempt "possibly delisted" logging at the
  source (`logging.getLogger("yfinance").setLevel(logging.CRITICAL)`)
  so a future unavailable ticker degrades to a quiet "N/A" tile instead
  of flooding the console — this is a broader fix than just removing
  the one bad ticker above.
- Replaced all uses of the deprecated `use_container_width` parameter
  (removed from Streamlit as of the version this project targets) with
  the current `width="stretch"`/`width="content"` API, across buttons,
  dataframes, plotly charts, and link buttons.

### Added
- 🇮🇳 **NSE Index Watch**: a native-Streamlit (no iframe), NSE-style card
  grid for Indian indices — Broad Market, Sectoral, Thematic, and
  Currency/Commodities tabs, colored tiles, advancing/declining summary
  counts, and a manual refresh button. Lives alongside the existing
  TradingView heatmap as the default tab under "📊 Live Market Heatmap".
  Data via `yfinance` rather than scraping nseindia.com directly — see
  `pinesprout/utils/index_watch.py` docstring for why.
- About page: custom brand colors for the social links — saffron for
  TradingView, white for X/Twitter, green for GitHub — targeted by
  `href` so they're independent of button order.

### Fixed
- Sidebar "not showing" was the browser persisting a collapsed sidebar
  state across visits (Streamlit's `initial_sidebar_state="expanded"`
  only applies on a session with no stored preference). Added an
  always-visible on-page hint pointing at the **»** expand control, and
  themed the top header/toolbar area and the sidebar-collapse button
  itself, which were previously left unstyled.

### Changed
- **Project renamed from "PineForge" to "PineSprout"** (package, CLI
  commands `pinesprout`/`psp`, env var prefix `PINESPROUT_`, all docs)
  to avoid a name collision with an existing product.

### Fixed
- Light theme now correctly re-themes Streamlit's own internal CSS
  variables (`--text-color`, `--background-color`, etc.), not just a
  handful of hand-picked selectors — text no longer disappears in light
  mode. The project's `.streamlit/config.toml` no longer hardcodes a
  static dark theme that fought the runtime toggle.
- Stock Heatmap widget no longer renders tiny/blank: added an explicit
  html/body CSS height reset and switched the widget config from a
  percentage height to a literal pixel value, since percentage
  resolution inside a dynamically-injected srcdoc iframe was racing the
  async TradingView script. Default height raised to 1000px (max 1800px).
- Added **NSE (National Stock Exchange of India)** as an exchange
  option for the heatmap — the previous list only had BSE/MSEI/NCDEX.

### Added
- ℹ️ **About** page: developer credit + TradingView/X/GitHub links for
  Khushal Jain, plus a feature-card showcase.
- PineSprout Studio: live scrolling market ticker (NIFTY 50, SENSEX,
  BANK NIFTY, commodities) via `pinesprout/utils/streamlit_ticker.py`.
- PineSprout Studio: customizable TradingView Stock Heatmap widget via
  `pinesprout/utils/market_heatmap.py`, covering US indices plus
  India (NSE, BSE, MSEI, NCDEX), Europe, and Asia-Pacific by exchange,
  exposed as a new sidebar mode.
- PineSprout Studio: Template Builder (`pinesprout/generators/
  template_builder.py`) — combinatorial indicator/strategy generator
  covering 25 indicators (trend/momentum/volatility/volume) x 4 signal
  patterns x indicator/strategy output x 3 risk-management styles, with
  freely adjustable numeric parameters. Every structural combination
  verified to lint clean with zero errors.
- PineSprout Studio: dark/light theme toggle via `pinesprout/utils/theme.py`.
- Market tools contributed by Khushal Jain.

## [0.1.0] - 2026-07-24

### Added
- Initial public release.
- Core engine: lexer, parser, formatter, linter, analyzer, optimizer, explainer, upgrader.
- AI-powered generation via the Anthropic API (`pinesprout generate`).
- Deterministic template scaffolds (`pinesprout template new`).
- README / HTML / Markdown documentation generators.
- Strategy/indicator analysis reports.
- SQLite-backed run history (`pinesprout history`).
- Plugin system (entry points + local `.pinesprout/plugins/`).
- Rich terminal UI with `--json` machine-readable output on every command.
- GitHub Actions CI and PyPI publish workflows.
