from collections import Counter
from datetime import datetime, timezone
from typing import Callable
import json
import uuid

import pandas as pd
import requests
import streamlit as st

from src.analytics import frequency_counter, overdue_gaps, recent_draw_summary, top_n
from src.jackpot_service import get_live_jackpot
from src.strategies import STRATEGIES, build_line, explain_line
from src import ui_components
from src.ticket_storage import load_tickets_from_localstorage, save_tickets_to_localstorage, deserialize_tickets


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


@st.cache_data(ttl=30 * 60)
def cached_jackpot():
    return get_live_jackpot()


def _fallback_jackpot_from_draw(draw: dict | None) -> int | None:
    if not draw:
        return None

    for key in ("estimatedJackpot", "jackpot", "jackpotAmount", "topPrize", "jackpot_amount"):
        raw = draw.get(key)
        if raw in (None, ""):
            continue
        cleaned = "".join(ch for ch in str(raw) if ch.isdigit())
        if cleaned:
            return int(cleaned)

    return None


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


def format_uk_date(date_str: str | None) -> str:
    if not date_str:
        return "Date unavailable"

    value = str(date_str).strip()
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y")
    except ValueError:
        for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, pattern).strftime("%d %b %Y")
            except ValueError:
                continue
    return value


def _draw_date_text(draw: dict) -> str:
    for key in ("date", "drawDate", "draw_date"):
        value = draw.get(key)
        if value not in (None, ""):
            return str(value)
    return ""




def _safe_ticket_lines(lines: list[dict] | None) -> list[dict]:
    validated: list[dict] = []
    for line in lines or []:
        if not isinstance(line, dict):
            continue

        main_numbers = line.get("main", [])
        stars = line.get("stars", [])

        if not isinstance(main_numbers, list) or not isinstance(stars, list):
            continue

        try:
            main_numbers = sorted(int(v) for v in main_numbers)
            stars = sorted(int(v) for v in stars)
        except (TypeError, ValueError):
            continue

        validated.append({"main": main_numbers, "stars": stars})

    return validated


def _new_ticket(lines: list[dict], strategy: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "draw_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "strategy": strategy,
        "lines": _safe_ticket_lines(lines),
        "status": "Pending",
        "notes": "",
    }


def _ensure_ticket_state() -> None:
    if "tickets" in st.session_state:
        return

    loaded_tickets = load_tickets_from_localstorage()
    st.session_state["tickets"] = loaded_tickets if isinstance(loaded_tickets, list) else []


def _persist_tickets() -> None:
    save_tickets_to_localstorage(st.session_state.get("tickets", []))

def render_insights(draws_df: pd.DataFrame) -> None:
    st.subheader("Insights")
    if draws_df.empty:
        st.info("No draw data available to generate insights.")
        return

    try:
        selected = st.segmented_control(
            "Range",
            ["Last 50", "Last 100", "Last 200", "All"],
            default="Last 100",
        )
    except Exception:
        selected = st.radio(
            "Range",
            ["Last 50", "Last 100", "Last 200", "All"],
            horizontal=True,
            index=1,
        )

    if selected == "Last 50":
        N = 50
    elif selected == "Last 100":
        N = 100
    elif selected == "Last 200":
        N = 200
    else:
        N = len(draws_df)

    filtered_df = draws_df.head(N).copy()

    if selected == "All":
        st.caption("Based on all draws")
    else:
        st.caption(f"Based on last {len(filtered_df)} draws")

    number_counter = Counter()
    for values in filtered_df["numbers"]:
        if isinstance(values, list):
            number_counter.update(values)

    if not number_counter:
        st.warning("No number frequencies available for the selected range.")
        return

    hot_number = number_counter.most_common(1)[0][0]
    cold_number = sorted(number_counter.items(), key=lambda item: (item[1], item[0]))[0][0]

    overdue_rows: list[dict] = []
    for number in range(1, 51):
        draws_since_seen = len(filtered_df)
        last_seen_date = "Never in range"

        for idx, row in filtered_df.iterrows():
            values = row.get("numbers", [])
            if isinstance(values, list) and number in values:
                draws_since_seen = int(idx)
                last_seen_date = format_uk_date(row.get("draw_date", ""))
                break

        overdue_rows.append(
            {
                "number": number,
                "draws_since_seen": draws_since_seen,
                "last_seen_date": last_seen_date,
            }
        )

    overdue_df = pd.DataFrame(overdue_rows).sort_values(
        ["draws_since_seen", "number"], ascending=[False, True]
    )
    overdue_number = int(overdue_df.iloc[0]["number"])

    col1, col2, col3 = st.columns(3)
    col1.metric("🔥 Hot", hot_number)
    col2.metric("❄️ Cold", cold_number)
    col3.metric("⏳ Overdue", overdue_number)

    freq_df = (
        pd.DataFrame(
            [{"number": number, "count": count} for number, count in number_counter.items()]
        )
        .sort_values("count", ascending=False)
        .head(10)
    )
    st.markdown("### Top 10 Frequency")
    st.bar_chart(freq_df, x="count", y="number", horizontal=True, use_container_width=True)

    st.markdown("### Most Overdue Numbers")
    st.dataframe(overdue_df.head(10), use_container_width=True, hide_index=True)

    trend_df = filtered_df.copy()
    trend_df["draw_date"] = trend_df["draw_date"].apply(format_uk_date)
    trend_df["main_total"] = trend_df["numbers"].apply(lambda values: sum(values) if isinstance(values, list) else 0)
    trend_df = trend_df.iloc[::-1]
    st.markdown("### Recent Trend")
    st.line_chart(trend_df.set_index("draw_date")[["main_total"]], use_container_width=True)


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


_ensure_ticket_state()
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
meta = cached_jackpot()
jackpot_amount = meta.jackpot_amount
if jackpot_amount is None:
    fallback_jackpot = _fallback_jackpot_from_draw(most_recent)
    jackpot_amount = f"£{fallback_jackpot:,}" if fallback_jackpot else None
jackpot_amount = jackpot_amount or "Jackpot unavailable"

jackpot_html = ui_components.render_jackpot_card(
    jackpot_amount=jackpot_amount,
    next_draw_date=format_uk_date(meta.next_draw_date) if meta.ok else None,
    next_draw_day=meta.next_draw_day if meta.ok else None,
)

if st.sidebar.checkbox("Debug jackpot source"):
    st.sidebar.write(meta)

st.markdown(
    render_last_result_banner(most_recent, brand_text="Wilkos LuckyLogic", jackpot_html=jackpot_html),
    unsafe_allow_html=True,
)

draws_df = pd.DataFrame(ordered_draws)
if not draws_df.empty:
    draws_df["draw_date"] = draws_df.apply(_draw_date_text, axis=1)
draws_df = draws_df.reset_index(drop=True)

tab_picks, tab_insights, tab_tickets = st.tabs(["Picks", "Insights", "Tickets"])

with tab_picks:
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

        generated_lines: list[dict] = []

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

                generated_lines.append({"main": nums, "stars": stars})
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

            if st.button("Save generated lines as ticket 🎟️", use_container_width=True):
                ticket = _new_ticket(lines=generated_lines, strategy=strategy)
                st.session_state["tickets"].append(ticket)
                _persist_tickets()
                st.success("Ticket saved on this device.")

            st.markdown(
                '<div class="disclaimer"><strong>Disclaimer:</strong> Lottery draws are random; this is for entertainment/variety.</div>',
                unsafe_allow_html=True,
            )

with tab_insights:
    render_insights(draws_df)

with tab_tickets:
    st.subheader("Tickets")
    st.caption("Save and track your generated lines here.")
    st.caption("Tickets are saved on this device (no login).")

    export_payload = json.dumps(st.session_state["tickets"], indent=2)
    export_col, import_col = st.columns(2)
    with export_col:
        st.download_button(
            "Export tickets (JSON)",
            data=export_payload,
            file_name="wilkos_luckylogic_tickets.json",
            mime="application/json",
            use_container_width=True,
        )

    with import_col:
        uploaded_file = st.file_uploader("Import tickets JSON", type=["json"], label_visibility="collapsed")
        if uploaded_file is not None:
            imported_text = uploaded_file.getvalue().decode("utf-8", errors="ignore")
            imported_tickets = deserialize_tickets(imported_text)
            if imported_tickets:
                st.session_state["tickets"] = imported_tickets
                _persist_tickets()
                st.success(f"Imported {len(imported_tickets)} ticket(s).")
            else:
                st.warning("Import file was empty or invalid JSON list.")

    tickets = st.session_state.get("tickets", [])
    if not tickets:
        st.info("No tickets saved yet. Go to Picks to generate lines and save a ticket.")
        if st.button("Go to Picks"):
            st.toast("Open the Picks tab to generate lines.")
    else:
        if st.button("Clear all tickets", type="secondary"):
            st.session_state["tickets"] = []
            _persist_tickets()
            st.success("All tickets cleared.")

        for index, ticket in enumerate(reversed(tickets), start=1):
            created_at = format_uk_date(ticket.get("created_at"))
            with st.expander(f"Ticket {index} • {ticket.get('strategy', 'Unknown strategy')} • {created_at}"):
                st.write(f"Status: {ticket.get('status', 'Pending')}")
                lines = _safe_ticket_lines(ticket.get("lines", []))
                for line_idx, line in enumerate(lines, start=1):
                    st.markdown(
                        f"**Line {line_idx}:** Main {', '.join(map(str, line['main']))} | Stars {', '.join(map(str, line['stars']))}"
                    )

                delete_key = f"delete_ticket_{ticket.get('id', index)}"
                if st.button("Delete ticket", key=delete_key):
                    st.session_state["tickets"] = [t for t in st.session_state["tickets"] if t.get("id") != ticket.get("id")]
                    _persist_tickets()
                    st.success("Ticket deleted.")
                    st.rerun()
