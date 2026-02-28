from __future__ import annotations

import streamlit as st


def render_balls(main_nums: list[int], stars: list[int]) -> None:
    main_markup = "".join([f'<span class="ball">{value}</span>' for value in main_nums])
    star_markup = "".join([f'<span class="ball star">{value}</span>' for value in stars])

    st.markdown(
        f"""
        <div class="ball-set" aria-label="Main numbers and lucky stars">
            <div class="ball-group" role="list" aria-label="Main numbers">{main_markup}</div>
            <div class="ball-divider">+</div>
            <div class="ball-group" role="list" aria-label="Lucky stars">{star_markup}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_insight_card(title: str, body: str, icon: str = "") -> None:
    st.markdown(
        f"""
        <div class="insight-card">
            <div class="insight-title"><span class="insight-icon">{icon}</span>{title}</div>
            <div class="insight-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def app_styles() -> str:
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --bg: #0b1220;
  --bg-elevated: #111b2f;
  --card-bg: rgba(17, 27, 47, 0.82);
  --card-border: rgba(148, 163, 184, 0.25);
  --text: #f8fafc;
  --muted: #cbd5e1;
  --accent: #3b82f6;
  --accent-soft: rgba(59, 130, 246, 0.18);
}

html, body, [class*="css"] {
  font-family: 'Inter', sans-serif;
}

.stApp {
  background:
    radial-gradient(circle at 8% 12%, rgba(56, 189, 248, 0.16), transparent 34%),
    radial-gradient(circle at 80% 20%, rgba(99, 102, 241, 0.15), transparent 34%),
    linear-gradient(180deg, #0a1222 0%, var(--bg) 100%);
  color: var(--text);
}

.block-container {
  padding-top: 1.4rem;
  padding-bottom: 1.6rem;
}

h1, h2, h3, h4,
p, li, span, div,
label, small,
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stCaptionContainer"],
[data-testid="stWidgetLabel"] {
  color: var(--text);
}

[data-testid="stMarkdownContainer"] p {
  line-height: 1.5;
}

[data-testid="stCaptionContainer"] {
  color: var(--muted) !important;
}

hr,
[data-testid="stDivider"] {
  border-color: var(--card-border) !important;
}

.hero {
  margin-bottom: 0.5rem;
}

.hero p {
  color: var(--muted);
  margin-top: 0.25rem;
}

.insight-card {
  border: 1px solid var(--card-border);
  border-radius: 0.95rem;
  padding: 0.85rem;
  min-height: 7.1rem;
  background: var(--card-bg);
  box-shadow: 0 12px 28px rgba(2, 6, 23, 0.2);
}

.insight-title {
  font-size: 0.92rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  margin-bottom: 0.45rem;
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.insight-icon {
  font-size: 1.02rem;
}

.insight-body {
  font-size: 0.9rem;
  color: var(--muted);
  line-height: 1.45;
}

.ball-set {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin: 0.25rem 0 0.65rem;
  flex-wrap: wrap;
}

.ball-group {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-wrap: wrap;
}

.ball-divider {
  color: var(--muted);
  font-weight: 700;
}

.ball {
  width: 2.2rem;
  height: 2.2rem;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 0.95rem;
  color: #ffffff;
  background: linear-gradient(180deg, #60a5fa, #1d4ed8);
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 6px 16px rgba(2, 6, 23, 0.35);
}

.ball.star {
  background: linear-gradient(180deg, #fde68a, #f59e0b);
  color: #1f2937;
  border-radius: 0.5rem;
  clip-path: polygon(50% 0%, 62% 35%, 100% 35%, 69% 57%, 82% 100%, 50% 72%, 18% 100%, 31% 57%, 0% 35%, 38% 35%);
  border: 1px solid rgba(180, 83, 9, 0.5);
}

.disclaimer {
  border-radius: 0.8rem;
  border: 1px solid var(--card-border);
  background: rgba(15, 23, 42, 0.75);
  color: var(--muted);
  padding: 0.8rem;
  font-size: 0.9rem;
}

/* BaseWeb selectbox: selected value + dropdown readability */
div[data-baseweb="select"] > div {
  background: var(--bg-elevated) !important;
  border-color: rgba(148, 163, 184, 0.35) !important;
}

div[data-baseweb="select"] span,
div[data-baseweb="select"] input,
div[data-baseweb="select"] div {
  color: #ffffff !important;
  opacity: 1 !important;
  font-weight: 500 !important;
  -webkit-text-fill-color: #ffffff !important;
}

div[data-baseweb="popover"] ul[role="listbox"] {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 0.55rem !important;
  box-shadow: 0 14px 30px rgba(2, 6, 23, 0.22) !important;
}

div[data-baseweb="popover"] ul[role="listbox"] li,
div[data-baseweb="popover"] ul[role="listbox"] li *,
div[data-baseweb="popover"] ul[role="listbox"] [role="option"],
div[data-baseweb="popover"] ul[role="listbox"] [role="option"] * {
  background: #ffffff !important;
  color: #111111 !important;
  -webkit-text-fill-color: #111111 !important;
  opacity: 1 !important;
  font-weight: 500 !important;
}

div[data-baseweb="popover"] ul[role="listbox"] li:hover,
div[data-baseweb="popover"] ul[role="listbox"] li:hover *,
div[data-baseweb="popover"] ul[role="listbox"] [role="option"]:hover,
div[data-baseweb="popover"] ul[role="listbox"] [role="option"]:hover *,
div[data-baseweb="popover"] ul[role="listbox"] [role="option"][data-highlighted="true"],
div[data-baseweb="popover"] ul[role="listbox"] [role="option"][data-highlighted="true"] * {
  background: #f1f3f6 !important;
  color: #000000 !important;
  -webkit-text-fill-color: #000000 !important;
  text-shadow: none !important;
  opacity: 1 !important;
}

div[data-baseweb="popover"] ul[role="listbox"] li[aria-selected="true"],
div[data-baseweb="popover"] ul[role="listbox"] li[aria-selected="true"] *,
div[data-baseweb="popover"] ul[role="listbox"] [role="option"][aria-selected="true"],
div[data-baseweb="popover"] ul[role="listbox"] [role="option"][aria-selected="true"] * {
  background: #e6f0ff !important;
  color: #000000 !important;
  -webkit-text-fill-color: #000000 !important;
  opacity: 1 !important;
}

div[data-baseweb="popover"] ul[role="listbox"] li[aria-disabled="true"],
div[data-baseweb="popover"] ul[role="listbox"] li[aria-disabled="true"] *,
div[data-baseweb="popover"] ul[role="listbox"] [role="option"][aria-disabled="true"],
div[data-baseweb="popover"] ul[role="listbox"] [role="option"][aria-disabled="true"] * {
  color: #111111 !important;
  -webkit-text-fill-color: #111111 !important;
  opacity: 1 !important;
}

/* Text/input guard rails for Streamlit theme overrides */
.stTextInput input,
.stNumberInput input,
.stSelectbox label,
.stSlider label,
.stCheckbox label,
[data-testid="stWidgetLabel"] {
  color: var(--text) !important;
}

@media (max-width: 640px) {
  .ball {
    width: 2rem;
    height: 2rem;
    font-size: 0.88rem;
  }

  .ball-set {
    gap: 0.45rem;
  }

  .insight-card {
    min-height: 6.2rem;
  }
}
</style>
"""
