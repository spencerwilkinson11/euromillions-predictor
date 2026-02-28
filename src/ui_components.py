from __future__ import annotations


from src.date_utils import format_uk_date
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

    return format_uk_date(value)


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


def render_last_result_banner(draw: dict | None, brand_text: str = "EUROMILLIONS", jackpot_html: str = "") -> str:
    safe_brand_text = escape(brand_text)
    if not draw:
        return (
            f'<div class="last-result-banner">'
            f'<div class="last-result-main">'
            f'<div class="last-result-brand">{safe_brand_text}</div>'
            f'<h2>Last result</h2>'
            f'<p class="last-result-date">No draw data available right now.</p>'
            f'</div>'
            f'<div class="last-result-right">'
            f'{jackpot_html}'
            f'</div>'
            f'</div>'
        )

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

    balls_markup = render_number_balls(main_numbers, lucky_stars, show_plus=False)

    draw_meta = ""
    if draw_no not in (None, ""):
        draw_meta += f'<div class="last-result-meta-item"><span class="meta-label">Draw</span><strong>#{draw_no}</strong></div>'

    formatted_jackpot = _format_jackpot(jackpot)
    if formatted_jackpot:
        draw_meta += f'<div class="last-result-meta-item"><span class="meta-label">Jackpot</span><strong>{formatted_jackpot}</strong></div>'

    meta_row_markup = f'<div class="last-result-meta-row">{draw_meta}</div>' if draw_meta else ""

    return (
        f'<div class="last-result-banner">'
        f'<div class="last-result-main">'
        f'<div class="last-result-brand">{safe_brand_text}</div>'
        f'<h2>Last result</h2>'
        f'<p class="last-result-date">{_format_draw_date(draw_date)}</p>'
        f'{balls_markup}'
        f'{meta_row_markup}'
        f'</div>'
        f'<div class="last-result-right">'
        f'{jackpot_html}'
        f'</div>'
        f'</div>'
    )


def render_jackpot_card(
    jackpot_amount=None,
    next_draw_date=None,
    next_draw_day=None,
    brand_text="EUROMILLIONS",
    **kwargs,
) -> str:
    """
    Renders jackpot card safely.
    Accepts flexible keyword arguments to prevent future crashes.
    """

    amount = escape(str(jackpot_amount)) if jackpot_amount else "Jackpot unavailable"

    meta = ""
    if next_draw_day or next_draw_date:
        formatted_draw_date = format_uk_date(next_draw_date) if next_draw_date else ""
        meta = f"<div class='jackpot-meta'>{escape(str(next_draw_day or ''))} {escape(str(formatted_draw_date or ''))}</div>"

    return (
        f'<div class="jackpot-card">'
        f'<div class="jackpot-brand">{escape(brand_text)}</div>'
        f'<div class="jackpot-amount">{amount}</div>'
        f'{meta}'
        f'<a class="jackpot-cta play-button" href="https://www.national-lottery.co.uk/results/euromillions" '
        f'target="_blank" rel="noopener noreferrer">Play for £2.50</a>'
        f'</div>'
    )

def render_app_header(app_name: str = "Wilkos LuckyLogic", tagline: str = "Smarter EuroMillions picks") -> str:
    return f"""
    <header class="app-header" aria-label="{escape(app_name)} app header">
        <div class="app-logo" aria-hidden="true">LL</div>
        <div class="app-header-copy">
            <h1 class="app-title">{escape(app_name)}</h1>
            <p class="app-subtitle">{escape(tagline)}</p>
        </div>
    </header>
    """


def render_balls(main_nums: list[int], stars: list[int]) -> None:
    st.markdown(
        render_number_balls(main_nums, stars),
        unsafe_allow_html=True,
    )


def render_number_balls(
    mains: list[int],
    stars: list[int] | None = None,
    matched_mains: set[int] | None = None,
    matched_stars: set[int] | None = None,
    show_plus: bool = True,
) -> str:
    matched_mains = matched_mains or set()
    matched_stars = matched_stars or set()

    main_markup = "".join(
        [
            f'<span class="premium-ball{" matched" if int(value) in matched_mains else ""}">{int(value)}</span>'
            for value in mains
        ]
    )
    stars_markup = "".join(
        [
            f'<span class="premium-ball premium-star{" matched" if int(value) in matched_stars else ""}"><span>{int(value)}</span></span>'
            for value in (stars or [])
        ]
    )
    divider_markup = '<div class="number-ball-divider">+</div>' if show_plus and stars_markup else ""

    return (
        '<div class="number-ball-set" aria-label="Main numbers and lucky stars">'
        f'<div class="number-ball-row" role="list" aria-label="Main numbers">{main_markup}</div>'
        f'{divider_markup}'
        f'<div class="number-ball-row" role="list" aria-label="Lucky stars">{stars_markup}</div>'
        '</div>'
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

    balls_markup = render_number_balls(main_nums, stars, show_plus=False)

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
        {balls_markup}
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
  animation: appFade 0.5s ease both;
}

@keyframes appFade {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

.block-container {
  padding-top: 0.55rem;
  padding-bottom: 1.0rem;
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


a:hover,
a:active,
a:visited:hover {
  color: #000000 !important;
  background: transparent !important;
}

.jackpot-cta:hover,
.jackpot-play:hover {
  color: #ffffff !important;
}

hr,
[data-testid="stDivider"] {
  border-color: var(--card-border) !important;
}

.app-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 0.4rem 0;
}

.app-logo {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: #f8fafc;
  background: linear-gradient(135deg, #2563eb 0%, #7c3aed 55%, #06b6d4 100%);
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 5px 14px rgba(59,130,246,0.35);
}

.app-header-copy {
  display: grid;
  gap: 0.05rem;
}

.app-title {
  line-height: 1.08;
  margin: 0;
  font-size: clamp(1.55rem, 2.1vw, 2.15rem);
  font-weight: 800;
  background: linear-gradient(90deg, #e2e8f0 0%, #93c5fd 40%, #a5b4fc 75%, #67e8f9 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.app-subtitle {
  margin-top: 2px;
  font-size: 0.85rem;
  line-height: 1.2;
  color: rgba(255,255,255,0.72);
}

.last-result-banner {
  margin: 0.4rem 0 1rem;
  border-radius: 1.1rem;
  border: 1px solid rgba(148, 163, 184, 0.3);
  background:
    linear-gradient(125deg, rgba(15, 23, 42, 0.92), rgba(17, 27, 47, 0.84)),
    radial-gradient(circle at 12% 18%, rgba(59, 130, 246, 0.16), transparent 30%),
    radial-gradient(circle at 85% 12%, rgba(56, 189, 248, 0.12), transparent 35%);
  backdrop-filter: blur(10px);
  box-shadow: 0 18px 42px rgba(2, 6, 23, 0.34);
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

.number-ball-set {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-wrap: wrap;
}

.number-ball-row {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.number-ball-divider {
  color: var(--muted);
  font-weight: 700;
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
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.premium-ball:hover {
  transform: translateY(-2px) scale(1.04);
  box-shadow: inset 0 -5px 10px rgba(15, 23, 42, 0.26), 0 13px 24px rgba(2, 6, 23, 0.42);
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

.last-result-right {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-width: 260px;
}

.last-result-right > [data-testid="stMarkdownPre"],
.last-result-right > .st-emotion-cache-acwcvw {
  display: none !important;
}

@media (min-width: 980px) {
  .last-result-right {
    flex-direction: row;
    align-items: stretch;
  }

  .jackpot-card {
    width: 260px;
  }
}


.jackpot-card {
  border-radius: 22px;
  background: linear-gradient(180deg, #f7b500 0%, #f5a800 100%);
  padding: 16px 16px 14px;
  box-shadow: 0 18px 40px rgba(2, 6, 23, 0.35);
  border: 1px solid rgba(11, 27, 140, 0.18);
  color: #0b1b8c;
  position: relative;
  overflow: hidden;
}

.jackpot-top {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.jackpot-day {
  font-weight: 800;
  font-size: 0.82rem;
  letter-spacing: 0.02em;
  color: #0b1b8c;
}

.jackpot-rule {
  height: 1px;
  background: rgba(11, 27, 140, 0.35);
}

.jackpot-brand {
  margin-top: 10px;
  font-weight: 900;
  letter-spacing: 0.02em;
  font-size: 1.15rem;
  color: #0b1b8c;
}

.jackpot-reg {
  font-size: 0.8rem;
  vertical-align: super;
  margin-left: 2px;
}

.jackpot-amount {
  margin-top: 10px;
  font-weight: 900;
  font-size: clamp(1.8rem, 3.6vw, 2.6rem);
  line-height: 1.05;
  color: #0b1b8c;
  word-break: break-word;
}

.jackpot-asterisk {
  font-size: 1.3rem;
  vertical-align: super;
}

.jackpot-label {
  margin-top: 8px;
  font-weight: 900;
  font-size: 1rem;
  color: #0b1b8c;
}

.jackpot-next {
  margin-top: 4px;
  font-size: 0.84rem;
  color: rgba(11, 27, 140, 0.85);
  font-weight: 700;
}

.jackpot-meta {
  margin-top: 4px;
  font-size: 0.84rem;
  color: rgba(11, 27, 140, 0.85);
  font-weight: 700;
}

.jackpot-play,
.jackpot-cta {
  display: block;
  margin-top: 16px;
  text-decoration: none;
  text-align: center;
  border-radius: 999px;
  background: #0b1b8c;
  color: #ffffff;
  font-weight: 900;
  padding: 12px 14px;
  box-shadow: 0 10px 24px rgba(11, 27, 140, 0.35);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

/* Keep Play for £2.50 label legible regardless of nested markup rendering. */
.play-button,
.play-button button,
.play-button button div,
.play-button button p,
.play-button span {
  color: #ffffff !important;
}

.play-button:hover,
.play-button button:hover,
.play-button button:hover div,
.play-button button:hover p,
.play-button:hover span {
  color: #ffffff !important;
}

.jackpot-play:hover,
.jackpot-cta:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 30px rgba(11, 27, 140, 0.45);
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

.em-results {
  display: grid;
  gap: 0.75rem;
  margin-top: 0.35rem;
}

.em-card {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 18px;
  padding: 16px;
  box-shadow: 0 12px 28px rgba(2, 6, 23, 0.22);
  backdrop-filter: blur(10px);
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

.premium-ball.matched {
  outline: 3px solid #FFD700;
  box-shadow: 0 0 0 2px rgba(255,215,0,0.35);
}

.ticket-match-list {
  display: grid;
  gap: 0.5rem;
  margin-bottom: 0.8rem;
}

.ticket-match-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  background: rgba(15, 23, 42, 0.45);
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 0.75rem;
  padding: 0.6rem;
}

.ticket-line-balls { margin: 0; }

.match-count-badge {
  width: 2.8rem;
  height: 2.8rem;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  font-weight: 800;
  color: #f8fafc;
  background: #0b1b8c;
  border: 2px solid #FFD700;
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

/* ===== FORCE CLEAN HOVER TEXT (NO GREY) ===== */
div[data-baseweb="popover"] ul li:hover,
div[data-baseweb="popover"] ul li:hover *,
div[data-baseweb="popover"] ul [role="option"]:hover,
div[data-baseweb="popover"] ul [role="option"]:hover * {
  background: #f3f4f6 !important;
  color: #000000 !important;
  -webkit-text-fill-color: #000000 !important;
  opacity: 1 !important;
}

div[data-baseweb="popover"] ul li,
div[data-baseweb="popover"] ul li *,
div[data-baseweb="popover"] ul [role="option"],
div[data-baseweb="popover"] ul [role="option"] * {
  color: #111111 !important;
  -webkit-text-fill-color: #111111 !important;
  opacity: 1 !important;
}

div[data-baseweb="popover"] ul li[aria-selected="true"],
div[data-baseweb="popover"] ul li[aria-selected="true"] *,
div[data-baseweb="popover"] ul [role="option"][aria-selected="true"],
div[data-baseweb="popover"] ul [role="option"][aria-selected="true"] * {
  background: #e6f0ff !important;
  color: #000000 !important;
  -webkit-text-fill-color: #000000 !important;
  opacity: 1 !important;
}

div[data-baseweb="popover"] * {
  text-shadow: none !important;
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
.stTextArea textarea,
.stNumberInput input,
.stSelectbox label,
.stSlider label,
.stCheckbox label,
[data-testid="stWidgetLabel"] {
  color: var(--text) !important;
}

/* Action controls: force dark theme so text never disappears on white widget surfaces */
.stButton > button,
.stDownloadButton > button,
button[kind="primary"],
button[kind="secondary"] {
  background: #0b1b2b !important;
  color: #ffffff !important;
  border: 2px solid rgba(255, 255, 255, 0.12) !important;
  border-radius: 12px !important;
  padding: 0.75rem 1rem !important;
}

.stButton > button:hover,
.stDownloadButton > button:hover,
.stButton > button:focus-visible,
.stDownloadButton > button:focus-visible {
  background: #0b1b2b !important;
  border: 2px solid rgba(255, 75, 75, 0.85) !important;
  color: #ffffff !important;
}

.stButton > button:disabled,
.stDownloadButton > button:disabled {
  background: rgba(11, 27, 43, 0.65) !important;
  color: rgba(255, 255, 255, 0.55) !important;
  border: 2px solid rgba(255, 255, 255, 0.08) !important;
}

div[data-testid="stButton"],
div[data-testid="stDownloadButton"] {
  background: transparent !important;
}

.stTextInput input,
.stTextArea textarea,
.stSelectbox div[data-baseweb="select"] > div {
  background: #0b1b2b !important;
  color: #ffffff !important;
  border: 1px solid rgba(255, 255, 255, 0.12) !important;
}

div[data-testid="stExpander"] summary {
  background: transparent !important;
  color: #ffffff !important;
}

/* Navigation tabs (Picks / Insights / Tickets): persistent active red border */
div[data-testid="stSegmentedControl"] button,
div[role="radiogroup"] label,
div[data-baseweb="button-group"] button {
  background: #0b1b2b !important;
  color: #ffffff !important;
  border: 2px solid transparent !important;
  border-radius: 12px !important;
  padding: 8px 16px !important;
  transition: all 0.2s ease !important;
}

div[data-testid="stSegmentedControl"] button:hover,
div[role="radiogroup"] label:hover,
div[data-baseweb="button-group"] button:hover {
  border: 2px solid #ff4b4b !important;
}

/* Keep this block after hover so the selected page stays highlighted */
div[data-testid="stSegmentedControl"] button[aria-pressed="true"],
div[data-testid="stSegmentedControl"] button[aria-selected="true"],
div[data-testid="stSegmentedControl"] [aria-selected="true"],
div[role="radiogroup"] input:checked + div,
div[role="radiogroup"] input:checked + label,
div[role="radiogroup"] label[data-checked="true"],
div[data-baseweb="button-group"] button[aria-selected="true"] {
  border: 2px solid #ff4b4b !important;
  background: #0b1b2b !important;
  color: #ffffff !important;
}

div[data-testid="stSegmentedControl"] *,
div[role="radiogroup"] *,
div[data-baseweb="button-group"] * {
  background: transparent !important;
}

div[data-testid="stSegmentedControl"] button[aria-pressed="true"],
div[data-testid="stSegmentedControl"] button[aria-selected="true"],
div[data-testid="stSegmentedControl"] [aria-selected="true"],
div[data-baseweb="button-group"] button[aria-selected="true"] {
  box-shadow: 0 0 0 1px rgba(255, 75, 75, 0.35) !important;
}

div[data-testid="stSegmentedControl"] button:focus,
div[role="radiogroup"] label:focus-within,
div[data-baseweb="button-group"] button:focus {
  outline: none !important;
  box-shadow: none !important;
}

@media (max-width: 640px) {
  .app-header {
    align-items: flex-start;
  }

  .app-logo {
    width: 2.8rem;
    height: 2.8rem;
    border-radius: 0.8rem;
    font-size: 1.05rem;
  }

  .premium-ball {
    width: 2rem;
    height: 2rem;
    font-size: 0.88rem;
  }

  .number-ball-set {
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

  .last-result-right {
    min-width: auto;
    width: 100%;
  }

  .jackpot-card {
    min-width: auto;
    width: 100%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .stApp,
  .premium-ball,
  .premium-star,
  .em-card {
    animation: none !important;
    transition: none !important;
  }
}
</style>
"""
