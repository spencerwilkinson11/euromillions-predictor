from __future__ import annotations

from src.date_utils import format_uk_date
from html import escape


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
        f'<a class="jackpot-cta wl-btn wl-btn--primary" href="https://www.national-lottery.co.uk/results/euromillions" '
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


def render_balls(main_nums: list[int], stars: list[int]) -> str:
    return render_number_balls(main_nums, stars)


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
            f'<span class="wl-ball wl-ball--main{" wl-ball--matched" if int(value) in matched_mains else ""}">{int(value)}</span>'
            for value in mains
        ]
    )
    stars_markup = "".join(
        [
            f'<span class="wl-ball wl-ball--star{" wl-ball--matched" if int(value) in matched_stars else ""}"><span>{int(value)}</span></span>'
            for value in (stars or [])
        ]
    )
    divider_markup = '<div class="number-ball-divider">+</div>' if show_plus and stars_markup else ""

    return (
        '<div class="number-ball-set wl-balls" aria-label="Main numbers and lucky stars">'
        f'<div class="number-ball-row wl-balls" role="list" aria-label="Main numbers">{main_markup}</div>'
        f'{divider_markup}'
        f'<div class="number-ball-row wl-balls" role="list" aria-label="Lucky stars">{stars_markup}</div>'
        '</div>'
    )


def render_insight_card(title: str, body: str, icon: str = "") -> str:
    return (
        f"""
        <div class="insight-card">
            <div class="insight-title"><span class="insight-icon">{icon}</span>{title}</div>
            <div class="insight-body">{body}</div>
        </div>
        """
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
    <article class="em-card" aria-label="Generated line {index}">
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

