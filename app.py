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


def _find_first_value(payload, keys):
    """Return the first non-empty value from known keys in a nested payload."""
    lowered_keys = {key.lower() for key in keys}

    if isinstance(payload, list):
        for item in payload:
            nested_value = _find_first_value(item, keys)
            if nested_value not in (None, ""):
                return nested_value
        return None

    if not isinstance(payload, dict):
        return None

    for key, value in payload.items():
        if key.lower() in lowered_keys and value not in (None, ""):
            return value

    for value in payload.values():
        if isinstance(value, (dict, list)):
            nested_value = _find_first_value(value, keys)
            if nested_value not in (None, ""):
                return nested_value

    return None


def _normalize_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "y", "1"}:
            return True
        if normalized in {"false", "no", "n", "0"}:
            return False
    return None


def _normalize_int(value):
    """Convert loosely-typed numeric values to int when possible."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        digits = "".join(ch for ch in value if ch.isdigit())
        if digits:
            return int(digits)
    return None


def _extract_jackpot_winners(draw):
    """Best-effort extraction of jackpot winners from inconsistent payloads."""
    direct_winners = _find_first_value(
        draw,
        [
            "jackpotWinners",
            "jackpot_winners",
            "numberOfJackpotWinners",
            "jackpotWinnerCount",
            "jackpotWinner",
            "topPrizeWinners",
        ],
    )
    direct_winners = _normalize_int(direct_winners)
    if direct_winners is not None:
        return direct_winners

    breakdown = _find_first_value(draw, ["prizeBreakdown", "breakdown", "prizes", "tiers"])
    if isinstance(breakdown, dict):
        for top_key in ["1", "1st", "first", "tier1", "rank1", "division1", "match5+2", "5+2"]:
            tier = breakdown.get(top_key)
            if isinstance(tier, dict):
                winners = _normalize_int(
                    _find_first_value(tier, ["winners", "winnerCount", "numberOfWinners", "tickets"])
                )
                if winners is not None:
                    return winners

    if isinstance(breakdown, list):
        for tier in breakdown:
            if not isinstance(tier, dict):
                continue
            rank = _find_first_value(tier, ["rank", "tier", "division", "category", "name"])
            normalized_rank = str(rank).strip().lower() if rank is not None else ""
            if normalized_rank in {"1", "1st", "first", "tier1", "division1", "match5+2", "5+2"}:
                winners = _normalize_int(
                    _find_first_value(tier, ["winners", "winnerCount", "numberOfWinners", "tickets"])
                )
                if winners is not None:
                    return winners

    return None


def _format_jackpot_value(value):
    """Normalize jackpot values into an easy-to-read Euro amount."""
    if value in (None, ""):
        return None

    if isinstance(value, (int, float)):
        return f"€{value:,.0f}"

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None

        compact = stripped.replace("€", "").replace(",", "").replace(" ", "")
        if compact.isdigit():
            return f"€{int(compact):,}"

        return stripped

    return str(value)


def extract_rollover_data(draw):
    """Extract rollover flag and jackpot details from a draw payload."""
    rollover = _find_first_value(
        draw,
        [
            "rollover",
            "isRollover",
            "is_rollover",
            "hasRollover",
            "rolloverFlag",
            "isRolloverDraw",
            "didRollover",
        ],
    )
    rollover = _normalize_bool(rollover)

    if rollover is None:
        jackpot_winners = _extract_jackpot_winners(draw)
        if jackpot_winners is not None:
            rollover = jackpot_winners == 0

    rollover_amount = _find_first_value(
        draw,
        [
            "rolloverAmount",
            "rollover_amount",
            "rolloverJackpot",
            "rollover_jackpot",
        ],
    )

    current_jackpot = _find_first_value(
        draw,
        [
            "jackpot",
            "jackpotAmount",
            "jackpot_amount",
            "prize",
            "amount",
        ],
    )

    next_jackpot = _find_first_value(
        draw,
        [
            "nextJackpot",
            "next_jackpot",
            "estimatedJackpot",
            "estimated_jackpot",
        ],
    )

    if isinstance(current_jackpot, dict):
        current_jackpot = _find_first_value(current_jackpot, ["amount", "value", "display", "formatted"]) or current_jackpot

    if isinstance(next_jackpot, dict):
        next_jackpot = _find_first_value(next_jackpot, ["amount", "value", "display", "formatted"]) or next_jackpot

    if isinstance(rollover_amount, dict):
        rollover_amount = _find_first_value(rollover_amount, ["amount", "value", "display", "formatted"]) or rollover_amount

    current_jackpot = _format_jackpot_value(current_jackpot)
    next_jackpot = _format_jackpot_value(next_jackpot)
    rollover_amount = _format_jackpot_value(rollover_amount)

    if rollover is None and rollover_amount:
        rollover = True

    display_jackpot = (
        next_jackpot
        if rollover is True and next_jackpot
        else rollover_amount or current_jackpot or next_jackpot
    )

    return rollover, display_jackpot, current_jackpot, next_jackpot, rollover_amount




def build_jackpot_summary(draw):
    """Build user-facing jackpot summary and detail text for the latest draw."""
    rollover_flag, jackpot_display, current_jackpot, next_jackpot, rollover_amount = extract_rollover_data(draw)

    if rollover_flag is True:
        status = "🔥 Rollover active"
        detail = "Prize pot rolled over from the previous draw."
    elif rollover_flag is False:
        status = "✅ No rollover"
        detail = "Jackpot was won in the previous draw."
    else:
        status = "ℹ️ Rollover status unavailable"
        detail = "Rollover flag is missing from the latest payload."

    if jackpot_display:
        status += f" — {jackpot_display}"

    if rollover_flag is True and current_jackpot and next_jackpot:
        detail = f"Rolled from {current_jackpot} to {next_jackpot}."
    elif rollover_flag is True and rollover_amount and not next_jackpot:
        detail = f"Latest payload reports a rollover amount of {rollover_amount}."

    return status, detail

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
    color: #f8fafc;
}

.block-container {
    max-width: 430px;
    padding-top: 1.2rem;
    padding-bottom: 1.6rem;
}

[data-testid="stAppViewContainer"] {
    display: flex;
    justify-content: center;
}

[data-testid="stAppViewContainer"] > .main {
    max-width: 470px;
    width: 100%;
    margin: 0 auto;
}

.main .block-container {
    background: linear-gradient(180deg, rgba(15, 23, 42, 0.88), rgba(15, 23, 42, 0.7));
    border: 1px solid rgba(148, 163, 184, 0.26);
    border-radius: 2.1rem;
    box-shadow: 0 24px 52px rgba(2, 6, 23, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.09);
    padding-left: 1.05rem;
    padding-right: 1.05rem;
    position: relative;
}

.main .block-container::before {
    content: "";
    position: absolute;
    top: 0.55rem;
    left: 50%;
    transform: translateX(-50%);
    width: 6rem;
    height: 0.35rem;
    border-radius: 999px;
    background: rgba(148, 163, 184, 0.35);
}

[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(180deg, rgba(15, 23, 42, 0.86), rgba(15, 23, 42, 0.65));
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 1rem;
    padding: 0.9rem;
}

.hero {margin-bottom: 1rem;}
.hero h1 {font-size: 1.75rem; margin-bottom: 0.3rem;}
.hero p {color: #e2e8f0; margin: 0; font-size: 0.96rem;}

h1, h2, h3, p, label, li, span, div, small {
    color: #f8fafc;
}

[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stCaptionContainer"],
[data-testid="stRadio"] label,
[data-testid="stSlider"] label,
[data-testid="stWidgetLabel"],
[data-testid="stMetricLabel"],
[data-testid="stMetricValue"] {
    color: #f8fafc !important;
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

@media (max-width: 640px) {
    .main .block-container {
        border-radius: 1.55rem;
    }
}
</style>
""",
    unsafe_allow_html=True,
)

jackpot_status = "⚠️ Jackpot unavailable"
jackpot_detail = "Could not fetch the latest EuroMillions draw right now."

try:
    latest_draws = fetch_draws()
except requests.RequestException:
    pass
else:
    if latest_draws:
        jackpot_status, jackpot_detail = build_jackpot_summary(latest_draws[0])

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
    st.subheader("EuroMillions Jackpot")
    st.metric("Latest jackpot", jackpot_status)
    st.caption(jackpot_detail)

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
