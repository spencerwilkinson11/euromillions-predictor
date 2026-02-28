from __future__ import annotations

from datetime import datetime
from html import escape

import streamlit as st


def _first_available(draw: dict, keys: tuple[str, ...]) -> object | None:
    for key in keys:
        if draw.get(key) not in (None, ""):
            return draw.get(key)
    return None


def _format_draw_date(value: object) -> str:
    if not value:
        return "Date unavailable"

    raw = str(value).strip()
    parsed: datetime | None = None

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                parsed = datetime.strptime(raw, pattern)
                break
            except ValueError:
                continue

    return parsed.strftime("%a %d %b %Y") if parsed else raw


def _format_jackpot(value: object) -> str | None:
    if value in (None, ""):
        return None

    if isinstance(value, (int, float)):
        return f"£{int(round(value)):,}"

    text = str(value).strip()
    digits = "".join(ch for ch in text if ch.isdigit() or ch in ".,")
    if digits:
        normalized = digits.replace(",", "")
        try:
            return f"£{int(float(normalized)):,}"
        except ValueError:
            pass

    return text


def render_last_result_banner(draw: dict | None, brand_text: str = "EUROMILLIONS") -> str:
    if not draw:
        return """
        <div class=\"last-result-banner\">
            <div class=\"last-result-main\">
                <div class=\"last-result-brand\">EUROMILLIONS</div>
                <h2>Last result</h2>
                <p class=\"last-result-date\">No draw data available right now.</p>
            </div>
            <div class=\"last-result-cta-panel\">
                <div class=\"last-result-cta-title\">Are you a winner?</div>
                <a class=\"last-result-cta-button\" href=\"https://www.national-lottery.co.uk/results/euromillions\" target=\"_blank\" rel=\"noopener noreferrer\">Check results</a>
            </div>
        </div>
        """

    main_numbers: list[int] = []
    for value in draw.get("numbers", []) or []:
        try:
            main_numbers.append(int(value))
        except (TypeError, ValueError):
            continue

    lucky_stars: list[int] = []
    for value in draw.get("stars", []) or []:
        try:
            lucky_stars.append(int(value))
        except (TypeError, ValueError):
            continue

    draw_no = _first_available(draw, ("drawNo", "drawNumber", "draw_number", "draw-no"))
    draw_date = _first_available(draw, ("date", "drawDate", "draw_date"))
    jackpot = _first_available(draw, ("jackpot", "jackpotAmount", "estimatedJackpot", "topPrize", "jackpot_amount"))

    draw_url = "https://www.national-lottery.co.uk/results/euromillions"
    if draw_no not in (None, ""):
        draw_url = f"{draw_url}/draw-details?drawNo={draw_no}"

    numbers_markup = "".join([f'<span class="premium-ball">{value}</span>' for value in main_numbers])
    stars_markup = "".join([f'<span class="premium-ball premium-star"><span>{value}</span></span>' for value in lucky_stars])

    draw_meta = ""
    if draw_no not in (None, ""):
        draw_meta += f'<div class="last-result-meta-item"><span class="meta-label">Draw</span><strong>#{draw_no}</strong></div>'

    formatted_jackpot = _format_jackpot(jackpot)
    if formatted_jackpot:
        draw_meta += f'<div class="last-result-meta-item"><span class="meta-label">Jackpot</span><strong>{formatted_jackpot}</strong></div>'

    return f"""
    <div class="last-result-banner">
        <div class="last-result-main">
            <div class="last-result-brand">{brand_text}</div>
            <h2>Last result</h2>
            <p class="last-result-date">{_format_draw_date(draw_date)}</p>
            <div class="last-result-balls" aria-label="Latest winning numbers and lucky stars">
                <div class="last-result-ball-row">{numbers_markup}</div>
                <div class="last-result-stars-row">{stars_markup}</div>
            </div>
            <div class="last-result-meta-row">{draw_meta}</div>
        </div>
        <div class="last-result-cta-panel">
            <div class="last-result-cta-title">Are you a winner?</div>
            <a class="last-result-cta-button" href="{draw_url}" target="_blank" rel="noopener noreferrer">Check results</a>
        </div>
    </div>
    """


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


def render_result_card(
    line_index: int,
    main_nums: list[int],
    stars: list[int],
    confidence: int,
    reasons: list[str],
) -> str:
    safe_confidence = max(0, min(100, int(confidence)))
    index = max(1, int(line_index))

    main_markup = "".join([f'<span class="premium-ball em-ball em-ball-main">{int(value)}</span>' for value in main_nums])
    stars_markup = "".join([f'<span class="premium-ball premium-star em-ball em-ball-star"><span>{int(value)}</span></span>' for value in stars])

    strategy_label: str | None = None
    display_reasons: list[str] = []
    for reason in reasons:
        text = str(reason).strip()
        if not text:
            continue
        if text.lower().startswith("strategy used:"):
            strategy_label = text.split(":", 1)[1].strip() or None
            continue
        if len(display_reasons) < 3:
            display_reasons.append(text)

    reason_markup = "".join([f"<li>{escape(reason)}</li>" for reason in display_reasons])
    strategy_markup = (
        f'<div class="em-strategy">Strategy used: <strong>{escape(strategy_label)}</strong></div>' if strategy_label else ""
    )

    return f"""
    <article class="em-card" style="--em-card-delay: {index * 70}ms" aria-label="Generated line {index}">
        <div class="em-card-header">
            <div class="em-card-title">Line {index}</div>
            <span class="em-badge" aria-label="Confidence {safe_confidence} out of 100">{safe_confidence}/100</span>
        </div>
        <div class="em-balls" aria-label="Main numbers and lucky stars">
            <div class="em-balls-main">{main_markup}</div>
            <div class="em-balls-stars">{stars_markup}</div>
        </div>
        <div class="em-meter" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{safe_confidence}" aria-label="Confidence {safe_confidence} out of 100">
            <span class="em-meter-fill" style="width: {safe_confidence}%;"></span>
        </div>
        <div class="em-meter-label">Confidence {safe_confidence}/100</div>
        <ul class="em-reasons">{reason_markup}</ul>
        {strategy_markup}
    </article>
    """


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

.last-result-banner {
  margin: 0.8rem 0 1rem;
  border-radius: 1.1rem;
  border: 1px solid rgba(148, 163, 184, 0.3);
  background:
    linear-gradient(125deg, rgba(15, 23, 42, 0.92), rgba(17, 27, 47, 0.84)),
    radial-gradient(circle at 12% 18%, rgba(59, 130, 246, 0.16), transparent 30%),
    radial-gradient(circle at 85% 12%, rgba(56, 189, 248, 0.12), transparent 35%);
  backdrop-filter: blur(8px);
  box-shadow: 0 18px 44px rgba(2, 6, 23, 0.35);
  padding: 1.15rem;
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.last-result-main {
  flex: 1;
}

.last-result-brand {
  font-size: 0.74rem;
  letter-spacing: 0.15em;
  font-weight: 700;
  color: #93c5fd;
}

.last-result-main h2 {
  margin: 0.2rem 0 0;
}

.last-result-date {
  margin: 0.2rem 0 0.65rem;
  color: var(--muted);
}

.last-result-balls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.last-result-ball-row,
.last-result-stars-row {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.premium-ball {
  width: 2.2rem;
  height: 2.2rem;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 0.92rem;
  color: #fff;
  position: relative;
  overflow: hidden;
  background: radial-gradient(circle at 28% 24%, #a5d8ff, #3b82f6 58%, #1d4ed8 100%);
  border: 1px solid rgba(255, 255, 255, 0.28);
  box-shadow: inset 0 -5px 10px rgba(15, 23, 42, 0.26), 0 10px 18px rgba(2, 6, 23, 0.35);
}

.premium-ball::before {
  content: "";
  position: absolute;
  top: 3px;
  left: 5px;
  width: 55%;
  height: 45%;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.65), rgba(255, 255, 255, 0));
}

.premium-star {
  background: radial-gradient(circle at 30% 20%, #fde68a, #f59e0b 60%, #b45309 100%);
  color: #111827;
}

.premium-star::after {
  content: "★";
  position: absolute;
  font-size: 0.45rem;
  top: 2px;
  right: 4px;
  color: rgba(120, 53, 15, 0.85);
}

.last-result-meta-row {
  margin-top: 0.7rem;
  display: flex;
  gap: 0.85rem;
  flex-wrap: wrap;
}

.last-result-meta-item {
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 0.7rem;
  background: rgba(15, 23, 42, 0.62);
  padding: 0.35rem 0.6rem;
  display: inline-flex;
  align-items: baseline;
  gap: 0.45rem;
}

.meta-label {
  font-size: 0.74rem;
  color: #93c5fd;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.last-result-cta-panel {
  min-width: 210px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 0.9rem;
  background: rgba(15, 23, 42, 0.55);
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  gap: 0.55rem;
}

.last-result-cta-title {
  font-weight: 700;
}

.last-result-cta-button {
  text-decoration: none;
  font-weight: 700;
  border-radius: 999px;
  padding: 0.48rem 0.9rem;
  color: #0f172a;
  background: linear-gradient(180deg, #fef08a, #fbbf24);
  border: 1px solid rgba(255, 255, 255, 0.48);
  box-shadow: 0 8px 18px rgba(245, 158, 11, 0.3);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
  animation: ctaPulse 2.4s ease-in-out infinite;
}

.last-result-cta-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 13px 24px rgba(245, 158, 11, 0.45);
}

@keyframes ctaPulse {
  0%, 100% { box-shadow: 0 8px 18px rgba(245, 158, 11, 0.3); }
  50% { box-shadow: 0 12px 25px rgba(251, 191, 36, 0.4); }
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

.em-results {
  display: grid;
  gap: 0.75rem;
  margin-top: 0.35rem;
}

.em-card {
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 18px;
  padding: 16px;
  box-shadow: 0 12px 26px rgba(2, 6, 23, 0.18);
  animation: emFadeIn 0.45s ease both;
  animation-delay: var(--em-card-delay, 0ms);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.em-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 16px 32px rgba(2, 6, 23, 0.28);
}

.em-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.8rem;
  margin-bottom: 0.75rem;
}

.em-card-title {
  color: #ffffff;
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.em-badge {
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 999px;
  padding: 0.22rem 0.6rem;
  color: #e2e8f0;
  background: rgba(15, 23, 42, 0.58);
  font-weight: 700;
  font-size: 0.8rem;
}

.em-balls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.em-balls-main,
.em-balls-stars {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.em-ball {
  width: 2rem;
  height: 2rem;
  font-size: 0.85rem;
}

.em-meter {
  width: 100%;
  height: 0.52rem;
  border-radius: 999px;
  margin-top: 0.75rem;
  background: rgba(148, 163, 184, 0.25);
  overflow: hidden;
}

.em-meter-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #38bdf8, #3b82f6 55%, #6366f1);
}

.em-meter-label {
  margin-top: 0.4rem;
  color: rgba(255, 255, 255, 0.76);
  font-size: 0.82rem;
}

.em-reasons {
  margin: 0.65rem 0 0;
  padding-left: 1.05rem;
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.9rem;
  line-height: 1.4;
}

.em-reasons li {
  margin-bottom: 0.2rem;
}

.em-strategy {
  margin-top: 0.5rem;
  color: rgba(255, 255, 255, 0.72);
  font-size: 0.8rem;
}

@keyframes emFadeIn {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
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

@media (max-width: 900px) {
  .last-result-banner {
    flex-direction: column;
  }

  .last-result-cta-panel {
    min-width: auto;
    width: 100%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .last-result-cta-button,
  .premium-ball,
  .premium-star,
  .em-card {
    animation: none !important;
    transition: none !important;
  }
}
</style>
"""
