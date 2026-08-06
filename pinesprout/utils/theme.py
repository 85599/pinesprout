"""
theme.py
Dark / Light theme toggle for PineSprout Studio.

Streamlit doesn't officially support switching `theme.base` at runtime
(that's normally fixed once in .streamlit/config.toml at startup), so
this module uses the standard workaround: keep the chosen theme in
st.session_state and inject a matching CSS override on every rerun.

Important: this CSS redefines Streamlit's OWN internal theming CSS
custom properties (--primary-color, --background-color,
--secondary-background-color, --text-color, and friends) at :root
scope, rather than only styling a few hand-picked selectors. Streamlit's
built-in stylesheet is written throughout using `var(--text-color)`
etc., so overriding the variables themselves -- instead of chasing every
individual element selector -- is what makes native widgets (headers,
captions, radio/checkbox labels, buttons, code blocks, dataframes, ...)
actually follow the toggle instead of staying stuck in whatever theme
.streamlit/config.toml set at startup. (This project's config.toml
intentionally does NOT set a static [theme] block, so it can't fight
this runtime override.)

Usage in your main app.py (near the very top, right after st.set_page_config):

    from theme import init_theme, theme_toggle, inject_theme_css

    init_theme()                # call once, sets default + reads session_state
    inject_theme_css()          # call once per rerun, injects the CSS

    # anywhere you want the toggle control (e.g. sidebar):
    theme_toggle(location=st.sidebar)
"""

from __future__ import annotations

from typing import Any

import streamlit as st

_THEME_KEY = "kj_theme"
_DEFAULT_THEME = "dark"


def _css_for(theme: str) -> str:
    if theme == "dark":
        bg, bg2, text, muted, border = "#0E1117", "#161B22", "#FAFAFA", "#9AA4B2", "#2A2F3A"
        code_bg = "#1C2129"
    else:
        bg, bg2, text, muted, border = "#FFFFFF", "#F5F7FA", "#14171A", "#5B6572", "#E1E5EA"
        code_bg = "#F0F2F5"
    accent = "#2962FF"

    return f"""
<style>
:root, .stApp {{
    --primary-color: {accent};
    --background-color: {bg};
    --secondary-background-color: {bg2};
    --text-color: {text};
    --text-color-light: {muted};
    --border-color: {border};
    --kj-bg: {bg};
    --kj-bg-secondary: {bg2};
    --kj-text: {text};
    --kj-text-muted: {muted};
    --kj-accent: {accent};
    --kj-border: {border};
    --kj-green: {"#26A65B" if theme == "dark" else "#178A4C"};
    --kj-red: {"#E5484D" if theme == "dark" else "#C6303E"};
}}

html, body {{ background-color: {bg}; }}
.stApp {{ background-color: {bg}; color: {text}; }}
.stApp, .stApp p, .stApp span, .stApp label, .stApp li {{ color: {text}; }}
h1, h2, h3, h4, h5, h6 {{ color: {text} !important; }}

[data-testid="stAppViewContainer"] {{ background-color: {bg}; }}
header[data-testid="stHeader"] {{
    background-color: {bg};
    color: {text};
}}
header[data-testid="stHeader"] * {{ color: {text} !important; fill: {text} !important; }}
[data-testid="stToolbar"] {{ color: {text}; }}
[data-testid="stToolbarActions"] button {{ color: {text} !important; }}
[data-testid="stSidebarCollapsedControl"] {{
    color: {text} !important;
    background-color: {bg2};
    border-radius: 6px;
}}
[data-testid="stSidebarCollapsedControl"] * {{ color: {text} !important; fill: {text} !important; }}
[data-testid="stSidebarCollapseButton"] * {{ color: {text} !important; fill: {text} !important; }}
#MainMenu {{ color: {text}; }}

section[data-testid="stSidebar"] {{ background-color: {bg2}; }}
section[data-testid="stSidebar"] * {{ color: {text}; }}

.stTabs [data-baseweb="tab-list"] {{ background-color: transparent; }}
.stTabs [data-baseweb="tab"] {{ color: {muted}; }}
.stTabs [aria-selected="true"] {{ color: {accent} !important; }}

div[data-testid="stMetric"] {{
    background-color: {bg2};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 10px 14px;
}}
div[data-testid="stMetric"] * {{ color: {text} !important; }}

div[data-testid="stMarkdownContainer"] {{ color: {text}; }}
[data-testid="stCaptionContainer"], .stCaption {{ color: {muted} !important; }}

.stTextInput input, .stTextArea textarea, .stNumberInput input {{
    background-color: {bg2};
    color: {text};
    border: 1px solid {border};
}}
div[data-baseweb="select"] > div {{
    background-color: {bg2};
    color: {text};
    border-color: {border};
}}
div[data-baseweb="popover"] {{ background-color: {bg2}; }}
li[role="option"] {{ color: {text}; background-color: {bg2}; }}

pre, code, .stCodeBlock {{ background-color: {code_bg} !important; }}

.stButton button, .stDownloadButton button, .stLinkButton a {{
    color: {text};
    border-color: {border};
}}
.stButton button[kind="primary"], .stDownloadButton button[kind="primary"] {{
    background-color: {accent};
    color: #FFFFFF;
    border-color: {accent};
}}

.stAlert {{ color: {text}; }}

.section-header {{
    font-weight: 600;
    font-size: 1.1rem;
    color: {accent};
    margin-top: 0.5rem;
}}
</style>
"""


def init_theme(default: str = _DEFAULT_THEME) -> None:
    """Call once near the top of the app. Sets the initial theme if not
    already chosen in this session."""
    if _THEME_KEY not in st.session_state:
        st.session_state[_THEME_KEY] = default


def get_theme() -> str:
    """Returns 'dark' or 'light' for the current session."""
    return str(st.session_state.get(_THEME_KEY, _DEFAULT_THEME))


def set_theme(theme: str) -> None:
    if theme not in ("dark", "light"):
        raise ValueError("theme must be 'dark' or 'light'")
    st.session_state[_THEME_KEY] = theme


def inject_theme_css() -> None:
    """Call once per app run (after init_theme) to apply the CSS override
    for whichever theme is currently active."""
    st.markdown(_css_for(get_theme()), unsafe_allow_html=True)


def theme_toggle(location: Any = st, key: str = "kj_theme_radio") -> None:
    """Renders a small dark/light toggle. Pass `st.sidebar` to place it
    there, or leave default to place it inline wherever called.

    If you render the toggle in more than one place (e.g. sidebar AND
    the About tab), pass a distinct `key` for each call -- Streamlit
    requires every widget key to be unique.
    """
    current = get_theme()
    labels = {"dark": "🌙 Dark", "light": "☀️ Light"}
    choice = location.radio(
        "Theme",
        options=["dark", "light"],
        format_func=lambda t: labels[t],
        index=0 if current == "dark" else 1,
        horizontal=True,
        key=key,
        label_visibility="collapsed",
    )
    if choice != current:
        set_theme(choice)
        # Deliberately no st.rerun() here: Streamlit already triggers an
        # automatic rerun whenever an interactive widget's value changes,
        # so this is redundant -- and calling it explicitly aborts the
        # *current* script pass immediately, before any widgets declared
        # further down the page (like the sidebar's mode radio) get
        # re-registered this run. Streamlit garbage-collects state for
        # widgets that weren't re-declared in a pass, which was silently
        # resetting navigation to the first sidebar option every time the
        # theme was toggled. The one-frame CSS lag this trades away
        # (this pass's `inject_theme_css()` already ran with the old
        # theme before this function was reached) self-corrects on
        # Streamlit's own automatic rerun and isn't perceptible in
        # practice.
