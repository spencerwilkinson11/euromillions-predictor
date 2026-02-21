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
.ball-row {display:flex; gap:0.5rem; margin:0.35rem 0 0.8rem 0; flex-wrap:wrap;}
.main-ball, .star-ball {
    width:2.25rem; height:2.25rem; border-radius:999px;
    display:flex; align-items:center; justify-content:center;
    font-weight:700; color:#fff;
    box-shadow:0 1px 5px rgba(0,0,0,0.25);
}
.main-ball {background: linear-gradient(180deg,#3b82f6,#1d4ed8);}
.star-ball {background: linear-gradient(180deg,#f59e0b,#d97706);}
.tip {font-size:0.9rem; opacity:0.9;}
</style>
""",
    unsafe_allow_html=True,
)

st.title("🎰 EuroMillions Number Generator")
st.write("Generate weighted picks from historical draws (just for fun).")

left, right = st.columns([1, 1])

with left:
    st.subheader("Options")
    pick_mode = st.radio("Pick mode", ["Weighted by history", "Pure random"], index=0)
    line_count = st.slider("Number of lines", min_value=1, max_value=10, value=3)
    max_draws = st.slider("Historical draws to use", min_value=50, max_value=500, value=200, step=50)
    generate = st.button("Generate Numbers 🎯", use_container_width=True)

with right:
    st.subheader("How this works")
    st.markdown(
        "- **Weighted mode**: numbers that appeared more often get higher chance.\n"
        "- **Pure random mode**: all seen numbers are equally likely.\n"
        "- Every line always contains **5 numbers + 2 stars**."
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
            st.markdown("**Line 1**")
            render_balls(preview_nums, "main-ball")
            render_balls(preview_stars, "star-ball")

            for idx in range(2, line_count + 1):
                nums, stars, _, _ = generate_line(draws, weighted=weighted)
                st.markdown(f"**Line {idx}**")
                render_balls(nums, "main-ball")
                render_balls(stars, "star-ball")

            st.info("For entertainment only — lottery outcomes are random and not predictable.")
            st.markdown('<p class="tip">Tip: generate a few batches and pick the line style you prefer.</p>', unsafe_allow_html=True)
