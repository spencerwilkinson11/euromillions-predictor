from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html import escape
from typing import Callable
import json
import uuid

import pandas as pd
import requests
import streamlit as st

from src.analytics import frequency_counter, overdue_gaps, recent_draw_summary, top_n
from src.date_utils import format_uk_date
from src.jackpot_service import get_live_jackpot
from src.strategies import STRATEGIES, build_line, explain_line
from src import ui_components
from src.ticket_storage import load_tickets_from_localstorage, save_tickets_to_localstorage


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
_render_number_balls = _resolve_ui_function("render_number_balls")


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


def render_number_balls(
    mains: list[int],
    stars: list[int] | None = None,
    matched_mains: set[int] | None = None,
    matched_stars: set[int] | None = None,
    show_plus: bool = True,
) -> str:
    if _render_number_balls:
        return _render_number_balls(
            mains,
            stars,
            matched_mains=matched_mains,
            matched_stars=matched_stars,
            show_plus=show_plus,
        )

    main_markup = "".join([f"<span>{int(value)}</span>" for value in mains])
    stars_markup = "".join([f"<span>{int(value)}</span>" for value in (stars or [])])
    return f"<div>{main_markup} + {stars_markup}</div>"

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


def _draw_date_text(draw: dict) -> str:
    for key in ("date", "drawDate", "draw_date"):
        value = draw.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _as_iso_date(value: object) -> str | None:
    if value in (None, ""):
        return None

    try:
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return datetime.fromisoformat(str(value).strip().replace("Z", "+00:00")).date().isoformat()
    except (TypeError, ValueError):
        return None


def upcoming_draw_dates(seed_iso: str | None, count: int = 6) -> list[date]:
    draw_days = {1, 4}  # Tuesday, Friday
    base_date = datetime.now(timezone.utc).date()
    parsed_seed = _as_iso_date(seed_iso)
    if parsed_seed:
        base_date = date.fromisoformat(parsed_seed)

    cursor = base_date
    draw_dates: list[date] = []
    while len(draw_dates) < count:
        if cursor.weekday() in draw_days and cursor not in draw_dates:
            draw_dates.append(cursor)
        cursor += timedelta(days=1)

    return draw_dates




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
    default_draw_date = datetime.now(timezone.utc).date().isoformat()
    return {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "draw_date": default_draw_date,
        "draw_label": format_uk_date(default_draw_date),
        "strategy": strategy,
        "lines": _safe_ticket_lines(lines),
        "status": "Pending",
        "notes": "",
    }


def _render_ticket_line_with_matches(line: dict, winning_mains: set[int], winning_stars: set[int]) -> str:
    mains = line.get("main", [])
    stars = line.get("stars", [])

    balls_markup = render_number_balls(
        mains,
        stars,
        matched_mains=(set(mains) & winning_mains),
        matched_stars=(set(stars) & winning_stars),
    )

    matches = sum(1 for value in mains if value in winning_mains) + sum(1 for value in stars if value in winning_stars)
    return (
        '<div class="ticket-match-line">'
        f'<div class="ticket-line-balls">{balls_markup}</div>'
        f'<div class="match-count-badge">{matches}</div>'
        '</div>'
    )


def render_your_tickets_section(most_recent_draw: dict | None) -> None:
    st.markdown("### Your Tickets")
    tickets = st.session_state.get("tickets", [])
    if not tickets:
        st.info("No saved tickets yet. Generate picks and save a ticket.")
        return

    recent_tickets = list(reversed(tickets[-3:]))
    last_result_date_iso = _as_iso_date(_draw_date_text(most_recent_draw or {}))

    for ticket in recent_tickets:
        created_at = format_uk_date(ticket.get("created_at"))
        strategy = escape(str(ticket.get("strategy", "Unknown strategy")))
        draw_date_iso = _as_iso_date(ticket.get("draw_date"))
        draw_label = ticket.get("draw_label") or format_uk_date(draw_date_iso)
        lines = _safe_ticket_lines(ticket.get("lines", []))[:5]
        draw_matches_latest = bool(last_result_date_iso and draw_date_iso == last_result_date_iso)

        winning_mains = (
            set(int(value) for value in (most_recent_draw or {}).get("numbers", []) if isinstance(value, int))
            if draw_matches_latest
            else set()
        )
        winning_stars = (
            set(int(value) for value in (most_recent_draw or {}).get("stars", []) if isinstance(value, int))
            if draw_matches_latest
            else set()
        )

        st.markdown(f"**{strategy}** · {draw_label} · Created {created_at}")
        lines_markup = "".join(
            [_render_ticket_line_with_matches(line, winning_mains=winning_mains, winning_stars=winning_stars) for line in lines]
        )
        st.markdown(f'<div class="ticket-match-list">{lines_markup}</div>', unsafe_allow_html=True)

    if st.button("View all in Tickets"):
        _navigate_to("Tickets")


def _ensure_ticket_state() -> None:
    if "tickets" not in st.session_state:
        loaded_tickets = load_tickets_from_localstorage()
        st.session_state["tickets"] = loaded_tickets if isinstance(loaded_tickets, list) else []

    if "last_generated_lines" not in st.session_state:
        st.session_state["last_generated_lines"] = None

    if "last_generated_meta" not in st.session_state:
        st.session_state["last_generated_meta"] = {}

    if "page" not in st.session_state:
        st.session_state["page"] = "Picks"


def _persist_tickets() -> None:
    save_tickets_to_localstorage(st.session_state.get("tickets", []))


def _navigate_to(page_name: str) -> None:
    st.session_state["page"] = page_name
    st.rerun()

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
    next_draw_date=meta.next_draw_date if meta.ok else None,
    next_draw_day=None,
)

draw_dates = upcoming_draw_dates(meta.next_draw_date if meta.ok else None)
draw_options = [{"label": format_uk_date(d), "value": d.isoformat()} for d in draw_dates]
selected_iso = st.session_state.get("selected_draw_date")
option_values = [option["value"] for option in draw_options]
if selected_iso not in option_values:
    selected_iso = draw_options[0]["value"] if draw_options else datetime.now(timezone.utc).date().isoformat()

draw_option_map = {option["label"]: option["value"] for option in draw_options}
selected_label = next((option["label"] for option in draw_options if option["value"] == selected_iso), format_uk_date(selected_iso))
st.session_state["selected_draw_date"] = selected_iso
st.session_state["selected_draw_label"] = selected_label

if st.sidebar.checkbox("Debug jackpot source"):
    st.sidebar.write(meta)

if st.sidebar.checkbox("Debug tickets state"):
    st.sidebar.write("tickets", len(st.session_state.get("tickets", [])))

st.markdown(
    render_last_result_banner(most_recent, brand_text="Wilkos LuckyLogic", jackpot_html=jackpot_html),
    unsafe_allow_html=True,
)

draws_df = pd.DataFrame(ordered_draws)
if not draws_df.empty:
    draws_df["draw_date"] = draws_df.apply(_draw_date_text, axis=1)
draws_df = draws_df.reset_index(drop=True)

pages = ["Picks", "Insights", "Tickets"]
current_idx = pages.index(st.session_state["page"]) if st.session_state["page"] in pages else 0

try:
    selected = st.segmented_control(
        label="Navigation",
        options=pages,
        default=pages[current_idx],
        key="nav_page",
        label_visibility="collapsed",
    )
except Exception:
    selected = st.radio(
        "Navigation",
        pages,
        horizontal=True,
        index=current_idx,
        key="nav_page",
        label_visibility="collapsed",
    )

if selected != st.session_state["page"]:
    st.session_state["page"] = selected

if st.session_state["page"] == "Picks":
    render_your_tickets_section(most_recent)
    left, main = st.columns([1, 2], gap="large")

    with left:
        st.subheader("Controls")
        selected_draw_label = st.selectbox(
            "Draw date",
            options=list(draw_option_map.keys()),
            index=list(draw_option_map.values()).index(st.session_state["selected_draw_date"]),
        )
        st.session_state["selected_draw_label"] = selected_draw_label
        st.session_state["selected_draw_date"] = draw_option_map[selected_draw_label]

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

        last_generated = st.session_state.get("last_generated_lines")
        if last_generated and isinstance(last_generated.get("lines"), list):
            st.caption("Your last generated set is ready to save.")
            if st.button("💾 Save as Ticket", use_container_width=True, type="secondary"):
                ticket = _new_ticket(
                    lines=last_generated.get("lines", []),
                    strategy=last_generated.get("strategy", "Balanced Mix"),
                )
                saved_draw_iso = last_generated.get("draw_date") or ticket["draw_date"]
                ticket["draw_date"] = saved_draw_iso
                ticket["draw_label"] = last_generated.get("draw_label") or format_uk_date(saved_draw_iso)
                st.session_state["tickets"].append(ticket)
                _persist_tickets()
                st.success("Ticket saved.")

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

            st.session_state["last_generated_lines"] = {
                "lines": generated_lines,
                "strategy": strategy,
                "draw_date": st.session_state["selected_draw_date"],
                "draw_label": st.session_state["selected_draw_label"],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            st.session_state["last_generated_meta"] = {
                "draw_date": st.session_state["selected_draw_date"],
                "draw_label": st.session_state["selected_draw_label"],
                "strategy": strategy,
                "line_count": line_count,
            }
            if st.button("Save generated lines as ticket 🎟️", use_container_width=True, type="secondary"):
                ticket = _new_ticket(lines=generated_lines, strategy=strategy)
                ticket["draw_date"] = st.session_state["selected_draw_date"]
                ticket["draw_label"] = st.session_state["selected_draw_label"]
                st.session_state["tickets"].append(ticket)
                _persist_tickets()
                st.success("Ticket saved.")

            st.markdown(
                '<div class="disclaimer"><strong>Disclaimer:</strong> Lottery draws are random; this is for entertainment/variety.</div>',
                unsafe_allow_html=True,
            )

elif st.session_state["page"] == "Insights":
    render_insights(draws_df)

else:
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
        st.empty()

    tickets = st.session_state.get("tickets", [])
    if not tickets:
        st.info("No tickets saved yet. Go to Picks to generate lines and save a ticket.")
        if st.button("Go to Picks"):
            _navigate_to("Picks")
    else:
        if st.button("Clear all tickets", type="secondary"):
            st.session_state["tickets"] = []
            _persist_tickets()
            st.success("All tickets cleared.")

        for index, ticket in enumerate(reversed(tickets), start=1):
            created_at = format_uk_date(ticket.get("created_at"))
            ticket_draw_label = ticket.get("draw_label") or format_uk_date(ticket.get("draw_date"))
            with st.expander(f"Ticket {index} • {ticket.get('strategy', 'Unknown strategy')} • {ticket_draw_label}"):
                st.caption(f"Created: {created_at}")
                st.write(f"Status: {ticket.get('status', 'Pending')}")
                lines = _safe_ticket_lines(ticket.get("lines", []))
                for line_idx, line in enumerate(lines, start=1):
                    st.markdown(f"**Line {line_idx}**")
                    st.markdown(render_number_balls(line["main"], line["stars"]), unsafe_allow_html=True)

                delete_key = f"delete_ticket_{ticket.get('id', index)}"
                if st.button("Delete ticket", key=delete_key):
                    st.session_state["tickets"] = [t for t in st.session_state["tickets"] if t.get("id") != ticket.get("id")]
                    _persist_tickets()
                    st.success("Ticket deleted.")
                    st.rerun()
