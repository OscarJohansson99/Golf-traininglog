
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date
import os

st.set_page_config(page_title="Golf Träningslogg", page_icon="⛳", layout="centered")

DATA_DIR = "data"
LOG_PATH = os.path.join(DATA_DIR, "logg.csv")
os.makedirs(DATA_DIR, exist_ok=True)

# --- Helpers ---
COLUMNS = ["datum", "pass", "kategori", "moment", "klubba", "värde", "anteckning"]

def init_log():
    if not os.path.exists(LOG_PATH):
        df = pd.DataFrame(columns=COLUMNS)
        df.to_csv(LOG_PATH, index=False, encoding="utf-8")

def read_log():
    init_log()
    try:
        df = pd.read_csv(LOG_PATH, encoding="utf-8")
    except Exception:
        df = pd.DataFrame(columns=COLUMNS)
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""
    return df

def append_row(row: dict):
    df = read_log()
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(LOG_PATH, index=False, encoding="utf-8")

def today_str():
    return date.today().isoformat()

# --- UI ---
st.title("⛳ Golf Träningslogg – Prototyp")
st.caption("Snabb inloggning av pass med autodatum, stora knappar och statistik.")

# Sidebar
view = st.sidebar.radio("Välj vy", ["Logga pass", "Statistik", "Data"])
st.sidebar.markdown("---")
df_all = read_log()
st.sidebar.download_button("⬇️ Ladda ner CSV", data=df_all.to_csv(index=False).encode("utf-8"),
                           file_name="golf_logg.csv", mime="text/csv")

# --- LOGGA PASS ---
if view == "Logga pass":
    st.header("🟢 Logga pass")
    pass_typ = st.selectbox("Välj träningspass", ["Range", "Närspel", "Bana"])

    if pass_typ == "Range":
        st.subheader("Träffbild")
        col1, col2, col3 = st.columns(3)
        if col1.button("➕ Mitt i"):
            append_row({"datum": today_str(), "pass": "Range", "kategori": "Träffbild",
                        "moment": "Mitt i", "klubba": "", "värde": 1, "anteckning": ""})
            st.success("Loggat: Mitt i (Range)")
        if col2.button("➕ Tåträff"):
            append_row({"datum": today_str(), "pass": "Range", "kategori": "Träffbild",
                        "moment": "Tåträff", "klubba": "", "värde": 1, "anteckning": ""})
            st.success("Loggat: Tåträff (Range)")
        if col3.button("➕ Hälträff"):
            append_row({"datum": today_str(), "pass": "Range", "kategori": "Träffbild",
                        "moment": "Hälträff", "klubba": "", "värde": 1, "anteckning": ""})
            st.success("Loggat: Hälträff (Range)")

        st.subheader("Tempo (rena träffar)")
        c1, c2 = st.columns(2)
        if c1.button("➕ 70% tempo – rent"):
            append_row({"datum": today_str(), "pass": "Range", "kategori": "Tempo",
                        "moment": "70% rent", "klubba": "", "värde": 1, "anteckning": ""})
            st.success("Loggat: 70% tempo – rent")
        if c2.button("➕ 90% tempo – rent"):
            append_row({"datum": today_str(), "pass": "Range", "kategori": "Tempo",
                        "moment": "90% rent", "klubba": "", "värde": 1, "anteckning": ""})
            st.success("Loggat: 90% tempo – rent")

        st.subheader("Längdkontroll (manual inmatning)")
        klubba = st.selectbox("Klubba", ["", "7i", "6i", "8i", "5i", "PW", "GW", "SW"])
        carry_m = st.number_input("Carry (m)", min_value=0, max_value=400, value=0, step=1)
        if st.button("➕ Logga carry"):
            append_row({"datum": today_str(), "pass": "Range", "kategori": "Längdkontroll",
                        "moment": "Carry", "klubba": klubba, "värde": carry_m, "anteckning": ""})
            st.success(f"Loggat: Carry {carry_m} m ({klubba})")

    elif pass_typ == "Närspel":
        st.subheader("Chippar")
        c1, c2 = st.columns(2)
        if c1.button("➕ Chip inom 2 m"):
            append_row({"datum": today_str(), "pass": "Närspel", "kategori": "Chippar",
                        "moment": "Inom 2m", "klubba": "", "värde": 1, "anteckning": ""})
            st.success("Loggat: Chip inom 2 m")
        if c2.button("➕ Chip utanför 2 m"):
            append_row({"datum": today_str(), "pass": "Närspel", "kategori": "Chippar",
                        "moment": "Utanför 2m", "klubba": "", "värde": 1, "anteckning": ""})
            st.info("Loggat: Chip utanför 2 m")

        st.subheader("Pitchar")
        p1, p2 = st.columns(2)
        if p1.button("➕ Pitch inom green/5 m"):
            append_row({"datum": today_str(), "pass": "Närspel", "kategori": "Pitchar",
                        "moment": "Inom 5m/green", "klubba": "", "värde": 1, "anteckning": ""})
            st.success("Loggat: Pitch inom 5 m / green")
        if p2.button("➕ Pitch utanför 5 m"):
            append_row({"datum": today_str(), "pass": "Närspel", "kategori": "Pitchar",
                        "moment": "Utanför 5m", "klubba": "", "värde": 1, "anteckning": ""})
            st.info("Loggat: Pitch utanför 5 m")

        st.subheader("Puttning")
        pp1, pp2 = st.columns(2)
        if pp1.button("➕ Kortputt i hål (1–2 m)"):
            append_row({"datum": today_str(), "pass": "Närspel", "kategori": "Puttning",
                        "moment": "Kortputt i hål", "klubba": "", "värde": 1, "anteckning": ""})
            st.success("Loggat: Kortputt i hål")
        dist = pp2.number_input("Långputt – snittavstånd kvar (m)", min_value=0.0, max_value=30.0, value=2.0, step=0.1)
        if pp2.button("➕ Logga långputt-snitt"):
            append_row({"datum": today_str(), "pass": "Närspel", "kategori": "Puttning",
                        "moment": "Långputt snitt", "klubba": "", "värde": dist, "anteckning": ""})
            st.info(f"Loggat: Långputt snitt {dist} m")

    elif pass_typ == "Bana":
        st.subheader("Runda (9 hål – logga per händelse)")
        b1, b2, b3 = st.columns(3)
        if b1.button("➕ Fairway träffad"):
            append_row({"datum": today_str(), "pass": "Bana", "kategori": "Runda",
                        "moment": "Fairway träffad", "klubba": "", "värde": 1, "anteckning": ""})
            st.success("Loggat: Fairway träffad")
        if b2.button("➕ GIR (green in regulation)"):
            append_row({"datum": today_str(), "pass": "Bana", "kategori": "Runda",
                        "moment": "GIR", "klubba": "", "värde": 1, "anteckning": ""})
            st.success("Loggat: GIR")
        if b3.button("➕ Putt"):
            append_row({"datum": today_str(), "pass": "Bana", "kategori": "Runda",
                        "moment": "Putt", "klubba": "", "värde": 1, "anteckning": ""})
            st.info("Loggat: Putt")
        note = st.text_input("Anteckning (valfritt)")
        if st.button("➕ Lägg till anteckning"):
            append_row({"datum": today_str(), "pass": "Bana", "kategori": "Anteckning",
                        "moment": "Kommentar", "klubba": "", "värde": 0, "anteckning": note})
            st.success("Anteckning sparad.")

# --- STATISTIK ---
elif view == "Statistik":
    st.header("📈 Statistik")
    df = df_all.copy()
    if df.empty:
        st.info("Ingen data ännu. Logga några poster under 'Logga pass'.")
    else:
        df['datum'] = pd.to_datetime(df['datum'], errors='coerce')

        st.subheader("Träffbild – Range")
        tb = df[(df['pass']=="Range") & (df['kategori']=="Träffbild")]
        if tb.empty:
            st.caption("Ingen träffbildsdata ännu.")
        else:
            pivot = tb.pivot_table(index='datum', columns='moment', values='värde', aggfunc='sum').fillna(0)
            st.dataframe(pivot)
            fig = plt.figure()
            pivot.plot(kind='bar', ax=plt.gca())
            plt.title("Träffbild per dag")
            plt.xlabel("Datum")
            plt.ylabel("Antal")
            st.pyplot(fig)

        st.subheader("Längdkontroll – Carry per klubba")
        lc = df[(df['pass']=="Range") & (df['kategori']=="Längdkontroll") & (df['moment']=="Carry") & (df['värde']>0)]
        if lc.empty:
            st.caption("Ingen carry-data ännu.")
        else:
            grp = lc.groupby(['datum','klubba'])['värde'].mean().reset_index()
            st.dataframe(grp)
            for klubba, sub in grp.groupby('klubba'):
                fig2 = plt.figure()
                plt.plot(sub['datum'], sub['värde'], marker='o')
                plt.title(f"Carry över tid – {klubba}")
                plt.xlabel("Datum")
                plt.ylabel("Meter")
                st.pyplot(fig2)

        st.subheader("Puttning – Kortputtar")
        pt = df[(df['pass']=="Närspel") & (df['kategori']=="Puttning") & (df['moment']=="Kortputt i hål")]
        if pt.empty:
            st.caption("Ingen kortputtsdata ännu.")
        else:
            ptd = pt.groupby('datum')['värde'].sum()
            fig3 = plt.figure()
            ptd.plot(kind='bar')
            plt.title("Kortputtar i hål per dag")
            plt.xlabel("Datum")
            plt.ylabel("Antal")
            st.pyplot(fig3)

# --- DATA ---
else:
    st.header("📄 Data")
    st.write("Alla loggade rader. Filen sparas som `data/logg.csv`.")
    st.dataframe(df_all)
    st.download_button("⬇️ Ladda ner hela loggen (CSV)",
                       data=df_all.to_csv(index=False).encode("utf-8"),
                       file_name="golf_logg.csv", mime="text/csv")
