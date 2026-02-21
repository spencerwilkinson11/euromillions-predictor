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
    balls = "".join([f'<span class="{class_name}">{value}</span>' for value in values])
    st.markdown(f'<div class="ball-row">{balls}</div>', unsafe_allow_html=True)


def stat_chip(label, value):
    st.markdown(
        f"""
        <div class="stat-chip">
            <span class="stat-label">{label}</span>
            <span class="stat-value">{value}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(circle at 10% 10%, #2b2f77 0%, #191b45 45%, #101229 100%);
        color: #e2e8f0;
    }
    .main > div {
        max-width: 420px;
        padding-top: 0.8rem;
        padding-bottom: 1.5rem;
    }
    h1, h2, h3, label, p, li, .stMarkdown, .stCaption {
        color: #e7ecff !important;
    }
    .hero-card {
        border-radius: 20px;
        padding: 1rem 1rem 1.15rem 1rem;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.14);
        backdrop-filter: blur(10px);
        margin-bottom: 0.9rem;
    }
    .hero-graphic {display:flex; align-items:center; justify-content:space-between; margin-bottom:0.65rem;}
    .hero-orb-row {display:flex; gap:0.35rem; align-items:center;}
    .hero-orb {
        width:1.75rem; height:1.75rem; border-radius:999px;
        display:flex; align-items:center; justify-content:center;
        font-size:0.72rem; font-weight:800; color:#ffffff;
        box-shadow:0 3px 10px rgba(0,0,0,0.25);
    }
    .hero-orb.main {background: linear-gradient(180deg,#60a5fa,#2563eb);}
    .hero-orb.star {background: linear-gradient(180deg,#fbbf24,#f59e0b);}
    .hero-badge {
        border-radius:999px; padding:0.28rem 0.62rem; font-size:0.72rem; font-weight:700;
        color:#dbe5ff; background:rgba(255,255,255,0.1); border:1px solid rgba(255,255,255,0.16);
    }
    .hero-title {
        font-size: 1.7rem; font-weight: 900; margin: 0; letter-spacing: 0.2px;
        background: linear-gradient(90deg, #f8fbff 0%, #c7d2fe 55%, #93c5fd 100%);
        -webkit-background-clip:text; background-clip:text; color: transparent;
    }
    .hero-sub {margin: 0.32rem 0 0 0; color: #dbe5ff; font-size: 0.95rem;}
    .ball-row {display: flex; gap: 0.5rem; margin: 0.35rem 0 0.7rem 0; flex-wrap: wrap;}
    .main-ball, .star-ball {
        width: 2.35rem; height: 2.35rem; border-radius: 999px;
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; color: #ffffff;
        box-shadow: 0 3px 12px rgba(0,0,0,0.28);
    }
    .main-ball {background: linear-gradient(180deg,#60a5fa,#2563eb);}
    .star-ball {background: linear-gradient(180deg,#fbbf24,#f59e0b);}
    .line-title {font-weight: 700; color: #f8fbff; margin-top: 0.5rem;}
    .stat-chip {
        display: flex; justify-content: space-between; align-items: center;
        border-radius: 12px; padding: 0.5rem 0.65rem; margin-bottom: 0.45rem;
        background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.1);
    }
    .stat-label {font-size: 0.84rem; color: #dbe5ff;}
    .stat-value {font-weight: 700; color: #f8fbff;}
    .tip {font-size: 0.88rem; color: #dbe5ff; margin-top: 0.45rem;}
    .disclaimer {
        margin-top: 0.7rem;
        border-radius: 12px;
        padding: 0.75rem 0.8rem;
        background: rgba(30, 41, 59, 0.55);
        border: 1px solid rgba(148, 163, 184, 0.3);
        color: #dbe5ff;
        font-size: 0.9rem;
        line-height: 1.4;
    }
    .stButton > button {
        border-radius: 14px;
        height: 3rem;
        font-weight: 700;
        border: none;
        color: #fff;
        background: linear-gradient(90deg, #4f46e5, #2563eb);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-card">
        <div class="hero-graphic">
            <div class="hero-orb-row">
                <span class="hero-orb main">7</span>
                <span class="hero-orb main">23</span>
                <span class="hero-orb main">44</span>
                <span class="hero-orb star">★</span>
            </div>
            <span class="hero-badge">Lucky Picks</span>
        </div>
        <p class="hero-title">EuroMillions Mobile Picks</p>
        <p class="hero-sub">Fast, fun line generation using recent draw history.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container(border=False):
    st.subheader("Customize")
    pick_mode = st.radio("Pick mode", ["Weighted by history", "Pure random"], index=0)
    line_count = st.slider("Number of lines", min_value=1, max_value=10, value=3)
    max_draws = st.slider("Historical draws", min_value=50, max_value=500, value=200, step=50)
    generate = st.button("Generate Numbers 🎯", use_container_width=True)
    st.caption("Weighted mode favors frequently drawn values.")

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
            st.subheader("Quick stats")
            preview_nums, preview_stars, num_counter, star_counter = generate_line(draws, weighted=weighted)
            stat_chip("Draws loaded", len(draws))
            stat_chip("Most frequent number", num_counter.most_common(1)[0][0])
            stat_chip("Most frequent star", star_counter.most_common(1)[0][0])

            st.subheader("Your lines")
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
                'Tip: if you want surprise-heavy picks, try Pure random mode.</div>',
                unsafe_allow_html=True,
            )

