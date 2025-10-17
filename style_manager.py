import streamlit as st

def apply_external_css(css_file_path: str):
    """Charge et applique un fichier CSS externe dans Streamlit."""
    with open(css_file_path) as f:
        css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
