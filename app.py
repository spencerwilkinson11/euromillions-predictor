from collections import Counter
from datetime import datetime, timezone
from typing import Callable
import xml.etree.ElementTree as ET

import pandas as pd
import requests
import streamlit as st

from src.analytics import frequency_counter, overdue_gaps, recent_draw_summary, top_n
from src.strategies import STRATEGIES, build_line, explain_line
from src import ui_components


def _resolve_ui_function(*names: str) -> Callable | None:
    for name in names:
        function = getattr(ui_components, name, None)
        if callable(function):
            return function
    return None


_app_styles = _resolve_ui_function("app_styles")
_render_insight_card = _resolve_ui_function("render_insight_card")
_render_last_result_banner = _resolve_ui_function("render_last_result_banner", "render_last_result")
_render_result_card = _resolve_ui_function("render_result_card")
_render_app_header = _resolve_ui_function("render_app_header")


def app_styles() -> str:
    if _app_styles:
        return _app_styles()
    return ""


def render_last_result_banner(draw: dict | None, brand_text: str = "Wilkos LuckyLogic", jackpot_html: str = "") -> str:
    if _render_last_result_banner:
        return _render_last_result_banner(draw, brand_text=brand_text, jackpot_html=jackpot_html)
    return (
        '<div class="last-result-banner"><div class="last-result-main"><h2>Last result</h2>'
        "<p>No draw data available right now.</p></div></div>"
    )


def render_result_card(line_index: int, main_nums: list[int], stars: list[int], confidence: int, reasons: list[str]) -> str:
    if _render_result_card:
        return _render_result_card(line_index, main_nums, stars, confidence, reasons)

    return (
        f"<div><strong>Line {line_index}</strong> — "
        f"Main: {', '.join(map(str, main_nums))} | Stars: {', '.join(map(str, stars))} | "
        f"Confidence: {confidence}/100<br/>{'<br/>'.join(reasons)}</div>"
    )


def render_insight_card(title: str, body: str, icon: str = "") -> None:
    if _render_insight_card:
        _render_insight_card(title, body, icon)
        return

    st.markdown(f"**{icon} {title}**")
    st.markdown(body, unsafe_allow_html=True)

st.set_page_config(page_title="Wilkos LuckyLogic", layout="wide")


@st.cache_data(ttl=60 * 60)
def fetch_draws():
    """Fetch draw history from the public API."""
    url = "https://euromillions.api.pedromealha.dev/v1/draws"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=60 * 60)
def fetch_national_lottery_euromillions_meta() -> dict:
    url = "https://www.national-lottery.co.uk/results/euromillions/draw-history/xml"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        root = ET.fromstring(response.text)

        latest_draw = None
        for draw in root.findall(".//draw-results"):
            latest_flag = draw.findtext("is-latest-draw")
            if (latest_flag or "").strip().upper() == "Y":
                latest_draw = draw
                break

        if latest_draw is None:
            latest_draw = root.find(".//draw-results")

        if latest_draw is None:
            return {"ok": False}

        jackpot_amount_text = latest_draw.findtext(".//game/jackpot-amount")
        next_draw_day = latest_draw.findtext(".//game/next-draw-day")

        jackpot_amount = None
        if jackpot_amount_text:
            cleaned = jackpot_amount_text.replace(",", "").strip()
            if cleaned.isdigit():
                jackpot_amount = int(cleaned)

        return {
            "ok": True,
            "jackpot_amount": jackpot_amount,
            "next_draw_day": (next_draw_day or "").strip().title(),
            "source": url,
        }
    except Exception:
        return {"ok": False}


def normalize_draws(draws: list[dict] | None) -> list[dict]:
    """Normalize draw payload values to stable integer lists for numbers/stars."""

    def _safe_int_list(values: list | None) -> list[int]:
        normalized_values: list[int] = []
        for value in values or []:
            if pd.isna(value):
                continue
            try:
                normalized_values.append(int(value))
            except (TypeError, ValueError):
                continue
        return normalized_values

    normalized: list[dict] = []
    for draw in draws or []:
        normalized_draw = dict(draw)
        normalized_draw["numbers"] = _safe_int_list(draw.get("numbers"))
        normalized_draw["stars"] = _safe_int_list(draw.get("stars"))
        normalized.append(normalized_draw)

    return normalized


def _parse_draw_timestamp(draw: dict) -> float:
    """Parse draw date formats and return a sortable UTC timestamp."""
    for key in ("date", "drawDate", "draw_date"):
        value = draw.get(key)
        if not value:
            continue

        text = str(value).strip()
        parsed_dt: datetime | None = None

        try:
            parsed_dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            for pattern in ("%Y-%m-%d", "%d/%m/%Y"):
                try:
                    parsed_dt = datetime.strptime(text, pattern)
                    break
                except ValueError:
                    continue

        if parsed_dt is None:
            continue

        if parsed_dt.tzinfo is None:
            parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
        else:
            parsed_dt = parsed_dt.astimezone(timezone.utc)

        return parsed_dt.timestamp()

    return float("-inf")


def prepare_draws(draws: list[dict] | None, history_n: int) -> list[dict]:
    """Normalize, sort newest-first by parsed date, and slice recent history."""
    normalized = normalize_draws(draws)
    ordered = sorted(normalized, key=_parse_draw_timestamp, reverse=True)
    return ordered[:history_n]


@st.cache_data(show_spinner=False)
def compute_insights(draws: list[dict], topn: int = 5):
    main_counter, star_counter = frequency_counter(draws)
    main_gap, star_gap = overdue_gaps(draws)

    return {
        "main_counter": main_counter,
        "star_counter": star_counter,
        "main_gap": main_gap,
        "star_gap": star_gap,
        "hot_main": top_n(main_counter, topn, reverse=True),
        "hot_star": top_n(star_counter, min(topn, 3), reverse=True),
        "cold_main": top_n(main_counter, topn, reverse=False),
        "cold_star": top_n(star_counter, min(topn, 3), reverse=False),
        "overdue_main": [n for n, _ in sorted(main_gap.items(), key=lambda item: item[1], reverse=True)[:topn]],
        "overdue_star": [s for s, _ in sorted(star_gap.items(), key=lambda item: item[1], reverse=True)[: min(topn, 3)]],
        "recent": recent_draw_summary(draws),
    }


st.markdown(app_styles(), unsafe_allow_html=True)
if _render_app_header:
    st.markdown(_render_app_header(app_name="Wilkos LuckyLogic", tagline="Smarter EuroMillions picks"), unsafe_allow_html=True)
else:
    st.title("Wilkos LuckyLogic")
    st.caption("Smarter EuroMillions picks")

try:
    all_draws = fetch_draws()
except requests.RequestException:
    all_draws = []

ordered_draws = prepare_draws(all_draws, len(all_draws) if all_draws else 0)
most_recent = ordered_draws[0] if ordered_draws else None
meta = fetch_national_lottery_euromillions_meta()
jackpot_html = (
    ui_components.render_jackpot_card(meta.get("jackpot_amount"), meta.get("next_draw_day"))
    if meta.get("ok")
    else ui_components.render_jackpot_card(None, None)
)
st.markdown(
    render_last_result_banner(most_recent, brand_text="Wilkos LuckyLogic", jackpot_html=jackpot_html),
    unsafe_allow_html=True,
)

left, main = st.columns([1, 2], gap="large")

with left:
    st.subheader("Controls")
    strategy = st.selectbox("Strategy", STRATEGIES, index=0)
    line_count = st.slider("Number of lines", min_value=1, max_value=10, value=4)
    max_draws = st.slider("Historical draws to use", min_value=50, max_value=500, value=250, step=50)
    topn = st.slider("Insight depth (Top N)", min_value=3, max_value=10, value=5)
    generate = st.button("Generate Decision Lines 🎯", use_container_width=True, type="primary")

    st.caption("Optional filters")
    include_last_draw = st.checkbox("Allow numbers from most recent draw", value=True)

with main:
    st.subheader("Generated Lines + Rationale")
    st.write("Select a strategy and generate lines to view confidence scoring and reasoning.")

if generate:
    with st.spinner("Fetching latest draw history..."):
        if not all_draws:
            try:
                all_draws = fetch_draws()
            except requests.RequestException as exc:
                st.error("Could not fetch draw data right now. Please try again in a moment.")
                st.caption(f"Technical details: {exc}")
                st.stop()

    draws = prepare_draws(all_draws, max_draws)
    if not draws:
        st.warning("No draw data available from the API.")
        st.stop()

    insights = compute_insights(draws, topn=topn)
    main_counter: Counter = insights["main_counter"]
    star_counter: Counter = insights["star_counter"]

    last_draw_numbers = set(insights["recent"]["numbers"])

    with main:
        m1, m2, m3 = st.columns(3)
        m1.metric("Draws loaded", len(draws))
        m2.metric("Most frequent main", main_counter.most_common(1)[0][0])
        m3.metric("Most frequent star", star_counter.most_common(1)[0][0])

        st.markdown('<div class="em-results">', unsafe_allow_html=True)
        for idx in range(1, line_count + 1):
            nums, stars = build_line(strategy, main_counter, star_counter, draws)

            if not include_last_draw:
                attempts = 0
                while set(nums).intersection(last_draw_numbers) and attempts < 10:
                    nums, stars = build_line(strategy, main_counter, star_counter, draws)
                    attempts += 1

            score, explanation = explain_line(
                nums,
                stars,
                main_counter=main_counter,
                star_counter=star_counter,
                main_gap=insights["main_gap"],
                strategy=strategy,
            )

            reasons = [*explanation[:3], f"Strategy used: {strategy}"]
            st.markdown(
                render_result_card(
                    line_index=idx,
                    main_nums=nums,
                    stars=stars,
                    confidence=score,
                    reasons=reasons,
                ),
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(
            '<div class="disclaimer"><strong>Disclaimer:</strong> Lottery draws are random; this is for entertainment/variety.</div>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.subheader("Insights")
    i1, i2, i3, i4 = st.columns(4)

    with i1:
        render_insight_card(
            "Hot numbers",
            f"Main: {', '.join(map(str, insights['hot_main']))}<br/>Stars: {', '.join(map(str, insights['hot_star']))}",
            "🔥",
        )
    with i2:
        render_insight_card(
            "Cold numbers",
            f"Main: {', '.join(map(str, insights['cold_main']))}<br/>Stars: {', '.join(map(str, insights['cold_star']))}",
            "❄️",
        )
    with i3:
        render_insight_card(
            "Overdue",
            f"Main: {', '.join(map(str, insights['overdue_main']))}<br/>Stars: {', '.join(map(str, insights['overdue_star']))}",
            "⏳",
        )
    with i4:
        recent = insights["recent"]
        render_insight_card(
            "Most recent draw",
            f"Date: {recent['date']}<br/>Numbers: {', '.join(map(str, recent['numbers']))}<br/>Stars: {', '.join(map(str, recent['stars']))}",
            "🕒",
        )

    st.subheader("Top Main Number Frequency")
    freq_df = pd.DataFrame(main_counter.most_common(10), columns=["Number", "Frequency"]).set_index("Number")
    st.bar_chart(freq_df)
