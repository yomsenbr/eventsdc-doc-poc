import requests, streamlit as st, os

API = os.environ.get("API_BASE", "http://localhost:8000")

st.title("EventsDC Document Search")

tab1, tab2 = st.tabs(["Ingest", "Ask/Search"])

with tab1:
    f = st.file_uploader("Upload PDF/DOCX/PPTX/TXT", type=["pdf","docx","pptx","txt"])
    if st.button("Ingest") and f:
        files = {"file": (f.name, f.getvalue())}
        r = requests.post(f"{API}/ingest", files=files, timeout=120)
        st.json(r.json())

with tab2:
    q = st.text_input("Your question or keywords", "what is our refund policy?")
    c1, c2, c3 = st.columns(3)
    if c1.button("Keyword"):
        st.json(requests.get(f"{API}/search/keyword", params={"q": q, "k": 5}).json())
    if c2.button("Hybrid"):
        st.json(requests.get(f"{API}/search/hybrid", params={"q": q, "k": 5}).json())
    if c3.button("Chat"):
        st.json(requests.get(f"{API}/chat", params={"q": q, "k": 5}).json())
