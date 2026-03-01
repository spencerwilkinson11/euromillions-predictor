def inject_css():
    from pathlib import Path
    import streamlit as st

    css_path = Path(__file__).resolve().parents[1] / "styles" / "app.css"

    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
