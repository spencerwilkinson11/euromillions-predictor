from __future__ import annotations

import streamlit as st


def render_balls(values: list[int], class_name: str) -> None:
    balls = "".join([f'<span class="{class_name}">{v}</span>' for v in values])
    st.markdown(f'<div class="ball-row">{balls}</div>', unsafe_allow_html=True)


def render_insight_card(title: str, body: str, icon: str = "") -> None:
    st.markdown(
        f"""
        <div class="insight-card">
            <div class="insight-title">{icon} {title}</div>
            <div class="insight-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def app_styles() -> str:
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
html, body, [class*="css"] {font-family: 'Inter', sans-serif;}
.stApp {
  background: radial-gradient(circle at 10% 10%, rgba(56, 189, 248, 0.18), transparent 30%),
              radial-gradient(circle at 85% 25%, rgba(59, 130, 246, 0.12), transparent 30%),
              linear-gradient(180deg, #0f172a 0%, #111827 100%);
  color: #f8fafc;
}
h1, h2, h3, p, label, li, span, div, small { color: #f8fafc; }
.main-ball, .star-ball {
  width:2.25rem;height:2.25rem;border-radius:999px;display:flex;align-items:center;justify-content:center;
  font-weight:800;color:#fff;box-shadow:0 8px 16px rgba(2,6,23,0.35);
}
.main-ball {background: linear-gradient(180deg,#60a5fa,#1d4ed8);}
.star-ball {background: linear-gradient(180deg,#fbbf24,#d97706);}
.ball-row {display:flex;gap:0.45rem;margin:0.15rem 0 0.6rem 0;flex-wrap:wrap;}
.hero {padding: 0.25rem 0 0.75rem 0;}
.hero p {opacity: 0.9;}
.insight-card {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 0.9rem;
  padding: 0.75rem;
  background: rgba(15, 23, 42, 0.65);
  min-height: 6.6rem;
}
.insight-title {font-weight: 700; margin-bottom: 0.35rem;}
.insight-body {font-size: 0.92rem; color: #e2e8f0;}
.disclaimer {
  border-radius: 0.8rem;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(15, 23, 42, 0.7);
  padding: 0.8rem;
  font-size: 0.9rem;
}
/* Improve Streamlit selectbox readability in dark theme */
div[data-baseweb="select"] > div {
  color: #f8fafc !important;
  background-color: rgba(30, 41, 59, 0.95) !important;
}
div[data-baseweb="select"] input {
  color: #f8fafc !important;
  -webkit-text-fill-color: #f8fafc !important;
}
div[role="listbox"] {
  background-color: #f8fafc !important;
}
div[role="option"] {
  color: #0f172a !important;
  background-color: #f8fafc !important;
}
div[role="option"][aria-selected="true"] {
  background-color: #dbeafe !important;
  color: #0f172a !important;
}
</style>
"""
