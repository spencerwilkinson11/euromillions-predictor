from datetime import date, datetime


def format_uk_date(d):
    """
    Accepts either:
    - ISO string "YYYY-MM-DD"
    - datetime/date object

    Returns:
    "Tue 03 Mar 2026"
    """
    try:
        if isinstance(d, str):
            dt = datetime.fromisoformat(d)
        else:
            dt = d

        return dt.strftime("%a %d %b %Y")
    except Exception:
        return str(d)

