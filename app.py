from collections import Counter

import pandas as pd
import requests
import streamlit as st

from src.analytics import frequency_counter, overdue_gaps, recent_draw_summary, top_n
from src.strategies import STRATEGIES, build_line, explain_line
from src.ui_components import app_styles, render_balls, render_insight_card

st.set_page_config(page_title="EuroMillions AI Decision Engine", layout="wide")


@st.cache_data(ttl=60 * 60)
def fetch_draws():
    """Fetch draw history from the public API."""
    url = "https://euromillions.api.pedromealha.dev/v1/draws"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


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
st.markdown(
    """
<div class="hero">
  <h1>🎰 EuroMillions AI Decision Engine</h1>
  <p>AI-assisted number ideas based on historical draws.</p>
</div>
""",
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
    try:
        with st.spinner("Fetching latest draw history..."):
            all_draws = fetch_draws()
    except requests.RequestException as exc:
        st.error("Could not fetch draw data right now. Please try again in a moment.")
        st.caption(f"Technical details: {exc}")
        st.stop()

    draws = normalize_draws(all_draws[:max_draws])
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

            with st.container(border=True):
                st.markdown(f"**Line {idx}**")
                render_balls(nums, stars)
                st.progress(score / 100, text=f"Confidence: {score}/100")
                for reason in explanation[:3]:
                    st.markdown(f"- {reason}")

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
