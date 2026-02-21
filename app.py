import random
from collections import Counter

import requests
import streamlit as st

st.set_page_config(page_title="EuroMillions Generator", layout="centered")


@st.cache_data(ttl=60 * 60)
def fetch_draws():
    """Fetch draw history from the public API."""
    url = "https://euromillions.api.pedromealha.dev/v1/draws"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def weighted_unique_pick(pool_counter, k):
    """Pick k unique values, weighted by frequency."""
    remaining = dict(pool_counter)
    picked = []

    for _ in range(min(k, len(remaining))):
        choices = list(remaining.keys())
        weights = list(remaining.values())
        selected = random.choices(choices, weights=weights, k=1)[0]
        picked.append(selected)
        remaining.pop(selected)

    return sorted(picked)


def random_unique_pick(values, k):
    return sorted(random.sample(sorted(set(values)), k=min(k, len(set(values)))))


def generate_line(draws, weighted=True):
    numbers, stars = [], []
    for draw in draws:
        numbers.extend(draw["numbers"])
        stars.extend(draw["stars"])

    if weighted:
        main_nums = weighted_unique_pick(Counter(numbers), 5)
        lucky_stars = weighted_unique_pick(Counter(stars), 2)
    else:
        main_nums = random_unique_pick(numbers, 5)
        lucky_stars = random_unique_pick(stars, 2)

    return main_nums, lucky_stars, Counter(numbers), Counter(stars)


def render_balls(values, class_name):
    balls = "".join([f'<span class="{class_name}">{v}</span>' for v in values])
    st.markdown(f'<div class="ball-row">{balls}</div>', unsafe_allow_html=True)


st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

html, body, [class*="css"]  {font-family: 'Inter', sans-serif;}

.stApp {
    background:
      radial-gradient(circle at 10% 10%, rgba(56, 189, 248, 0.18), transparent 30%),
      radial-gradient(circle at 85% 25%, rgba(59, 130, 246, 0.12), transparent 30%),
      linear-gradient(180deg, #0f172a 0%, #111827 100%);
    color: #e2e8f0;
}

.block-container {
    max-width: 460px;
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(180deg, rgba(15, 23, 42, 0.86), rgba(15, 23, 42, 0.65));
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 1rem;
    padding: 0.9rem;
}

.hero {margin-bottom: 1rem;}
.hero h1 {font-size: 1.75rem; margin-bottom: 0.3rem; color: #f8fafc;}
.hero p {color: #dbe7ff; margin: 0; font-size: 0.96rem;}

h2, h3, [data-testid="stWidgetLabel"] p {
    color: #eaf2ff !important;
}

[data-testid="stCaptionContainer"] p,
.stRadio label p,
.stSlider label p,
.stSlider [data-testid="stTickBarMin"],
.stSlider [data-testid="stTickBarMax"],
.stSlider [data-testid="stSliderTickBarMin"],
.stSlider [data-testid="stSliderTickBarMax"] {
    color: #b9cae8 !important;
    opacity: 1 !important;
}

.stRadio [role="radiogroup"] label {
    color: #d7e4fb !important;
}

[data-testid="stMetric"] {
    border-radius: 0.85rem;
    border: 1px solid rgba(148, 163, 184, 0.2);
    background: rgba(15, 23, 42, 0.7);
    padding: 0.55rem;
}

.line-title {
    font-weight: 700;
    margin-top: 0.65rem;
    margin-bottom: 0.25rem;
    color: #f8fafc;
}

.ball-row {display:flex; gap:0.5rem; margin:0.2rem 0 0.7rem 0; flex-wrap:wrap;}
.main-ball, .star-ball {
    width:2.35rem;
    height:2.35rem;
    border-radius:999px;
    display:flex;
    align-items:center;
    justify-content:center;
    font-weight:800;
    font-size: 0.95rem;
    color:#fff;
    box-shadow:0 8px 16px rgba(2,6,23,0.35);
}
.main-ball {
    background: linear-gradient(180deg,#60a5fa,#1d4ed8);
    border: 1px solid rgba(255,255,255,0.26);
}
.star-ball {
    background: linear-gradient(180deg,#fbbf24,#d97706);
    border: 1px solid rgba(255,255,255,0.24);
}

.disclaimer {
    border-radius: 0.8rem;
    border: 1px solid rgba(148, 163, 184, 0.22);
    background: rgba(15, 23, 42, 0.7);
    padding: 0.8rem;
    font-size: 0.9rem;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="hero">
  <h1>🎰 EuroMillions Generator</h1>
  <p>Smart, clean number picks inspired by historical draws.</p>
</div>
""",
    unsafe_allow_html=True,
)

with st.container(border=True):
    st.subheader("Create your play lines")
    pick_mode = st.radio("Pick mode", ["Weighted by history", "Pure random"], index=0, horizontal=True)
    line_count = st.slider("Number of lines", min_value=1, max_value=10, value=3)
    max_draws = st.slider("Historical draws to use", min_value=50, max_value=500, value=200, step=50)
    generate = st.button("Generate Numbers 🎯", use_container_width=True, type="primary")

with st.container(border=True):
    st.caption("How it works")
    st.markdown(
        "- **Weighted mode**: numbers that appeared more often get higher chance.\n"
        "- **Pure random mode**: all seen numbers are equally likely.\n"
        "- Every line contains **5 numbers + 2 stars**."
    )

if generate:
    try:
        with st.spinner("Fetching latest draw history..."):
            all_draws = fetch_draws()
    except requests.RequestException as exc:
        st.error("Could not fetch draw data right now. Please try again in a moment.")
        st.caption(f"Technical details: {exc}")
    else:
        draws = all_draws[:max_draws]
        weighted = pick_mode == "Weighted by history"

        if not draws:
            st.warning("No draw data available from the API.")
        else:
            preview_nums, preview_stars, num_counter, star_counter = generate_line(draws, weighted=weighted)

            c1, c2, c3 = st.columns(3)
            c1.metric("Draws loaded", len(draws))
            c2.metric("Most frequent number", num_counter.most_common(1)[0][0])
            c3.metric("Most frequent star", star_counter.most_common(1)[0][0])

            st.divider()
            st.subheader("Your Lines")

            # First line from preview so we can reuse computed counters for metrics.
            st.markdown('<p class="line-title">Line 1</p>', unsafe_allow_html=True)
            render_balls(preview_nums, "main-ball")
            render_balls(preview_stars, "star-ball")

            for idx in range(2, line_count + 1):
                nums, stars, _, _ = generate_line(draws, weighted=weighted)
                st.markdown(f'<p class="line-title">Line {idx}</p>', unsafe_allow_html=True)
                render_balls(nums, "main-ball")
                render_balls(stars, "star-ball")

            st.markdown(
                '<div class="disclaimer"><strong>For entertainment only.</strong> '
                'Lottery outcomes are random and not predictable.<br/>'
                'Tip: generate a few batches and pick the line style you prefer.</div>',
                unsafe_allow_html=True,
            )
