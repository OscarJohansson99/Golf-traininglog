
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date, datetime, timedelta
import os, json

st.set_page_config(page_title="Golf Träningslogg", page_icon="⛳", layout="centered")

# -----------------------------
# Paths & constants
# -----------------------------
DATA_DIR = "data"
VIDEO_DIR = os.path.join(DATA_DIR, "videos")
IMG_DIR = os.path.join(DATA_DIR, "images")
LOG_PATH = os.path.join(DATA_DIR, "logg.csv")
VIDEO_META = os.path.join(DATA_DIR, "videos.csv")
PROFILE_JSON = os.path.join(DATA_DIR, "profile.json")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

COLUMNS = ["datum", "pass", "kategori", "moment", "klubba", "värde", "anteckning"]
VIDEO_COLUMNS = ["ts","filnamn","storlek_bytes","format","vinkel","klubba","miljo","miss","kommentar"]

# -----------------------------
# Data helpers
# -----------------------------
def init_log():
    if not os.path.exists(LOG_PATH):
        pd.DataFrame(columns=COLUMNS).to_csv(LOG_PATH, index=False, encoding="utf-8")
    if not os.path.exists(VIDEO_META):
        pd.DataFrame(columns=VIDEO_COLUMNS).to_csv(VIDEO_META, index=False, encoding="utf-8")
    if not os.path.exists(PROFILE_JSON):
        with open(PROFILE_JSON, "w", encoding="utf-8") as f:
            json.dump({"swing_speed_value": 95, "swing_speed_unit": "mph", "shaft_flex": "R"}, f)

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

def write_log(df: pd.DataFrame):
    df.to_csv(LOG_PATH, index=False, encoding="utf-8")

def append_row(row: dict):
    df = read_log()
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    write_log(df)

def read_videos():
    init_log()
    try:
        dv = pd.read_csv(VIDEO_META, encoding="utf-8")
    except Exception:
        dv = pd.DataFrame(columns=VIDEO_COLUMNS)
    for c in VIDEO_COLUMNS:
        if c not in dv.columns:
            dv[c] = ""
    return dv

def append_video_meta(meta: dict):
    dv = read_videos()
    dv = pd.concat([dv, pd.DataFrame([meta])], ignore_index=True)
    dv.to_csv(VIDEO_META, index=False, encoding="utf-8")

def read_profile():
    init_log()
    try:
        with open(PROFILE_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"swing_speed_value": 95, "swing_speed_unit": "mph", "shaft_flex": "R"}

def write_profile(p):
    with open(PROFILE_JSON, "w", encoding="utf-8") as f:
        json.dump(p, f)

def today_str():
    return date.today().isoformat()

# -----------------------------
# Session state
# -----------------------------
def ss_get(k, v):
    if k not in st.session_state:
        st.session_state[k] = v
    return st.session_state[k]

# Coach counters per dag
ss_get("toe_count", 0); ss_get("heel_count", 0); ss_get("thin_count", 0); ss_get("fat_count", 0)
ss_get("slice_count", 0); ss_get("hook_count", 0)
ss_get("counter_date", today_str())

def reset_daily_counters():
    if st.session_state.counter_date != today_str():
        st.session_state.counter_date = today_str()
        st.session_state.toe_count = 0
        st.session_state.heel_count = 0
        st.session_state.thin_count = 0
        st.session_state.fat_count = 0
        st.session_state.slice_count = 0
        st.session_state.hook_count = 0

# Quick carry & sessions
CLUBS = [
    "LW (60deg)","SW (56deg)","GW (52deg)","PW (48deg)",
    "9i","8i","7i","6i","5i","4i",
    "Hybrid 4","Hybrid 3",
    "Tra-5","Tra-3","Driver"
]

ss_get("last_club", "7i")
ss_get("last_carry", 150)
ss_get("fast_mode", True)
ss_get("pass_active", False)
ss_get("pass_rows", [])
ss_get("pass_started_at", None)

def log_and_track(row):
    append_row(row)
    if st.session_state.pass_active:
        st.session_state.pass_rows.append(row)

def start_pass():
    if not st.session_state.pass_active:
        st.session_state.pass_active = True
        st.session_state.pass_rows = []
        st.session_state.pass_started_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        st.success(f"Pass startat {st.session_state.pass_started_at}")

def end_pass_summary():
    rows = st.session_state.pass_rows
    if not rows:
        st.info("Inget loggat i detta pass ännu.")
        return
    df = pd.DataFrame(rows, columns=COLUMNS)
    st.subheader("📌 Sammanställning av pass")
    st.caption(f"Start: {st.session_state.pass_started_at}  •  Slut: {datetime.now().strftime('%Y-%m-%d %H:%M')}  •  Antal loggar: {len(df)}")

    # Träffbild
    tb = df[(df["kategori"]=="Träffbild")]
    if not tb.empty:
        counts = tb["moment"].value_counts().to_dict()
        mitt = counts.get("Mitt i", 0); toe  = counts.get("Tåträff", 0); heel = counts.get("Hälträff", 0)
        st.write(f"**Träffbild** – Mitt i: {mitt} • Tå: {toe} • Häl: {heel}")
        strengths, weaknesses = [], []
        if mitt >= max(toe, heel): strengths.append("Många rena träffar (mitt i)")
        if toe > 0 and toe >= heel: weaknesses.append(f"Många tåträffar ({toe}) – stå närmare, balans, armar förlängs")
        if heel > 0 and heel > toe: weaknesses.append(f"Många hälträffar ({heel}) – håll spacing, lite längre ifrån")
        if strengths: st.success("**Styrkor:** " + " • ".join(strengths))
        if weaknesses: st.warning("**Att träna på:** " + " • ".join(weaknesses))

    # Kontakt
    kt = df[(df["kategori"]=="Kontakt")]
    if not kt.empty:
        cts = kt["moment"].value_counts().to_dict()
        thin = cts.get("Topp", 0); fat  = cts.get("Duff", 0)
        st.write(f"**Kontakt** – Topp: {thin} • Duff: {fat}")
        todo = []
        if thin > 0: todo.append("Topp: behåll posture, markkontakt efter bollen (myntdrill)")
        if fat  > 0: todo.append("Duff: vikt mot framfot, turf på strecket framför bollen")
        if todo: st.warning("**Kontakt – fokus:** " + " • ".join(todo))

    # Driver-missar
    dv = df[(df["kategori"]=="Driver")]
    if not dv.empty:
        dvc = dv["moment"].value_counts().to_dict()
        s_cnt = dvc.get("Slice", 0); h_cnt = dvc.get("Hook", 0); n_cnt = dvc.get("Neutral", 0)
        st.write(f"**Driver** – Slice: {s_cnt} • Hook: {h_cnt} • Neutral: {n_cnt}")
        reco = []
        if s_cnt >= 3: reco.append("Slice: jobba med face-to-path (stäng face), in-to-out-känsla, hög tee.")
        if h_cnt >= 3: reco.append("Hook: svagare grepp, neutralare path, kontrollerad release.")
        if reco: st.warning("**Driver – fokus:** " + " • ".join(reco))

    # Carry per klubba
    lc = df[(df["kategori"]=="Längdkontroll") & (df["moment"]=="Carry")]
    if not lc.empty:
        lc["värde"] = pd.to_numeric(lc["värde"], errors="coerce")
        lc = lc[lc["värde"]>0]
        grp = lc.groupby("klubba")["värde"].agg(["count","mean","std"]).reset_index().rename(
            columns={"count":"Antal","mean":"Snitt (m)","std":"Spridning (m)"})
        st.write("**Carry per klubba (detta pass)**")
        st.dataframe(grp, use_container_width=True)

        if not grp.empty:
            good = grp.sort_values("Spridning (m)", ascending=True).head(1)
            bad  = grp.sort_values("Spridning (m)", ascending=False).head(1)
            if not good.empty:
                s = good.iloc[0]
                st.success(f"Stabilast carry: **{s['klubba']}** – spridning {0 if pd.isna(s['Spridning (m)']) else round(s['Spridning (m)'],1)} m")
            if not bad.empty and bad.iloc[0]['Antal'] >= 3 and pd.notnull(bad.iloc[0]['Spridning (m)']):
                s = bad.iloc[0]
                st.warning(f"Mest ojämn carry: **{s['klubba']}** – spridning {round(s['Spridning (m)'],1)} m")

    # markera pass-slut i loggen
    log_and_track({"datum": today_str(), "pass":"SYSTEM", "kategori":"Session", "moment":"End", "klubba":"", "värde":0, "anteckning":"Avslutat pass"})
    st.session_state.pass_active = False
    st.session_state.pass_rows = []
    st.balloons()

# Simple coach toasts
def show_toe_tips(): st.toast("Tåträff – stå närmare, balans mitt/framfot.", icon="⚠️")
def show_heel_tips(): st.toast("Hälträff – håll spacing, lite längre ifrån.", icon="⚠️")
def show_thin_tips(): st.toast("Topp – behåll posture, markkontakt efter bollen.", icon="⚠️")
def show_fat_tips(): st.toast("Duff – vikt mot framfot, turf framför bollen.", icon="⚠️")

def show_slice_tips():
    st.toast("Driver slice – jobba face & path.", icon="⚠️")
    with st.expander("Enkel drill mot slice (öppna)"):
        img_path = os.path.join(IMG_DIR, "slice_grip.png")
        if os.path.exists(img_path):
            st.image(img_path, caption="Starkare grepp – rotera händerna lite åt höger på greppet.")
        else:
            st.info("Lägg valfri bild här: data/images/slice_grip.png (visas som exempel).")
        st.markdown("""
**Gör så här (superenkelt):**
- Grepp: rotera händerna lite **åt höger** (se 3–4 knogar vänster hand).
- Tee **högt** och slå **uppåt** på bollen.
- Lägg en peg bakom bollen, **strax utanför** svingbanan – missa peggen (sväng inifrån).
""")

def show_hook_tips():
    st.toast("Driver hook – neutralisera grepp & path.", icon="⚠️")
    with st.expander("Enkel drill mot hook (öppna)"):
        img_path = os.path.join(IMG_DIR, "hook_grip.png")
        if os.path.exists(img_path):
            st.image(img_path, caption="Svagare grepp – rotera händerna lite åt vänster på greppet.")
        else:
            st.info("Lägg valfri bild här: data/images/hook_grip.png (visas som exempel).")
        st.markdown("""
**Gör så här (superenkelt):**
- Grepp: rotera händerna lite **åt vänster** (1–2 knogar syns).
- Starta bollen **rakt/ett snäpp vänster** om mål (anti in-to-out).
- Känn att klubbhuvudet **inte** stänger så mycket (håll face lite längre öppet).
""")

# -----------------------------
# Equipment feedback
# -----------------------------
def speed_to_mps(value, unit):
    if unit == "mph":
        return value * 0.44704
    return value

def suggest_shaft(speed_value, speed_unit, current_flex):
    v = speed_to_mps(speed_value, speed_unit)
    # Very rough buckets for driver clubhead speed
    if v < 36:      target = "A/L"   # < ~80 mph
    elif v < 42:    target = "R"     # ~80–94 mph
    elif v < 47:    target = "S"     # ~94–105 mph
    else:           target = "X"     # > ~105 mph
    msg = None
    if target == "A/L" and current_flex not in ["A","L"]:
        msg = "Din svinghastighet är låg/moderat. Testa mjukare skaft (A/L) för att hjälpa klubbhuvudet att stänga."
    if target == "R" and current_flex != "R":
        msg = "Din svinghastighet passar Regular (R). Ett R-skaft kan ge bättre timing."
    if target == "S" and current_flex != "S":
        msg = "Din svinghastighet passar Stiff (S). Ett styvare skaft kan stabilisera face."
    if target == "X" and current_flex != "X":
        msg = "Din svinghastighet är hög. Extra Stiff (X) kan minska spridning."
    return target, msg

# -----------------------------
# UI shell
# -----------------------------
st.title("⛳ Golf Träningslogg – Coach Prototyp (All‑in‑One)")
st.caption("Dashboard, pass-sammanställning, snabb carry, driver slice/hook, draw/fade, video, profil med svingdata.")

view = st.sidebar.radio("Välj vy", ["Dashboard","Logga pass","Statistik","Video","Profil","Data"])
st.sidebar.markdown("---")
df_all = read_log()
st.sidebar.download_button("⬇️ Ladda ner CSV", data=df_all.to_csv(index=False).encode("utf-8"),
                           file_name="golf_logg.csv", mime="text/csv")

# Dagens räknare
st.sidebar.markdown("### Dagens räknare")
st.sidebar.write(f"👣 Tå: {st.session_state.toe_count}  •  🦶 Häl: {st.session_state.heel_count}")
st.sidebar.write(f"⬆️ Topp: {st.session_state.thin_count}  •  🟫 Duff: {st.session_state.fat_count}")
st.sidebar.write(f"🚗 Slice: {st.session_state.slice_count}  •  🔁 Hook: {st.session_state.hook_count}")

# -----------------------------
# DASHBOARD
# -----------------------------
if view == "Dashboard":
    st.header("📊 Dashboard")
    profile = read_profile()

    if df_all.empty:
        st.info("Logga några slag först under 'Logga pass' så fylls din dashboard.")
    else:
        df = df_all.copy()
        df["datum"] = pd.to_datetime(df["datum"], errors="coerce")
        df = df.sort_values("datum")
        days = st.selectbox("Visa data för", ["Senaste 7 dagar","Senaste 30 dagar","All tid"])
        if days == "Senaste 7 dagar":
            start = pd.Timestamp.today().normalize() - pd.Timedelta(days=6)
            df = df[df["datum"] >= start]
        elif days == "Senaste 30 dagar":
            start = pd.Timestamp.today().normalize() - pd.Timedelta(days=29)
            df = df[df["datum"] >= start]

        colA, colB, colC = st.columns(3)
        tb = df[(df["pass"]=="Range") & (df["kategori"]=="Träffbild")]
        clean = (tb["moment"]=="Mitt i").sum() if not tb.empty else 0
        misses = len(tb) - clean if not tb.empty else 0
        ratio = 0 if (clean+misses)==0 else round(100*clean/(clean+misses))
        colA.metric("Rena träffar", clean)
        colB.metric("Missar (tå/häl)", misses)
        colC.metric("Träff%-range", f"{ratio}%")

        # Driver overview
        dv = df[(df["pass"]=="Range") & (df["kategori"]=="Driver")]
        s_cnt = (dv["moment"]=="Slice").sum() if not dv.empty else 0
        h_cnt = (dv["moment"]=="Hook").sum() if not dv.empty else 0
        n_cnt = (dv["moment"]=="Neutral").sum() if not dv.empty else 0
        st.subheader("🚗 Driver – översikt")
        st.write(f"Slice: {s_cnt} • Hook: {h_cnt} • Neutral: {n_cnt}")
        # Equipment suggestion inline
        target, msg = suggest_shaft(profile.get("swing_speed_value",95), profile.get("swing_speed_unit","mph"), profile.get("shaft_flex","R"))
        if msg:
            st.info(f"Utrustning: {msg} (rekommenderad flex: {target})")

        if s_cnt >= h_cnt and s_cnt > 0:
            st.warning("Driver: Vanligaste missen är Slice – starkare grepp, in-to-out, högre tee.", icon="⚠️")
        elif h_cnt > 0:
            st.warning("Driver: Vanligaste missen är Hook – svagare grepp, neutralare path, kontrollerad release.", icon="⚠️")
        else:
            st.success("Driver: Ser stabilt ut – fortsätt.")

        # Carry per klubba
        lc = df[(df["pass"]=="Range") & (df["kategori"]=="Längdkontroll") & (df["moment"]=="Carry")]
        lc["värde"] = pd.to_numeric(lc["värde"], errors="coerce")
        lc = lc[lc["värde"]>0]
        if not lc.empty:
            st.subheader("Carry per klubba")
            g = lc.groupby("klubba")["värde"].agg(["count","mean","std"]).reset_index()
            g = g.rename(columns={"count":"Antal","mean":"Snitt (m)","std":"Spridning (m)"})
            st.dataframe(g, use_container_width=True)

        # Träfftrend
        if not tb.empty:
            trend = tb.assign(ok = (tb["moment"]=="Mitt i").astype(int)).groupby("datum")["ok"].sum()
            fig = plt.figure()
            trend.plot(kind='bar')
            plt.title("Rena träffar per dag"); plt.xlabel("Datum"); plt.ylabel("Antal")
            st.pyplot(fig)

# -----------------------------
# LOGGA PASS
# -----------------------------
elif view == "Logga pass":
    reset_daily_counters()
    cols = st.columns(2)
    if cols[0].button("▶️ Starta pass", disabled=st.session_state.pass_active):
        start_pass()
    if cols[1].button("⛳ Avsluta träningspass", disabled=not st.session_state.pass_active):
        end_pass_summary()

    st.header("🟢 Logga pass")
    pass_typ = st.selectbox("Välj träningspass", ["Range", "Närspel", "Bana"])

    if pass_typ == "Range":
        st.subheader("Träffbild")
        col1, col2, col3 = st.columns(3)
        if col1.button("➕ Mitt i"):
            log_and_track({"datum": today_str(), "pass":"Range","kategori":"Träffbild","moment":"Mitt i","klubba":"","värde":1,"anteckning":""})
            st.success("Loggat: Mitt i")
        if col2.button("➕ Tåträff"):
            log_and_track({"datum": today_str(), "pass":"Range","kategori":"Träffbild","moment":"Tåträff","klubba":"","värde":1,"anteckning":""})
            st.session_state.toe_count += 1
            st.info(f"Tåträff #{st.session_state.toe_count} idag")
            if st.session_state.toe_count == 5: show_toe_tips()
        if col3.button("➕ Hälträff"):
            log_and_track({"datum": today_str(), "pass":"Range","kategori":"Träffbild","moment":"Hälträff","klubba":"","värde":1,"anteckning":""})
            st.session_state.heel_count += 1
            st.info(f"Hälträff #{st.session_state.heel_count} idag")
            if st.session_state.heel_count == 5: show_heel_tips()

        st.subheader("Kontakt")
        k1, k2 = st.columns(2)
        if k1.button("➕ Topp"):
            log_and_track({"datum": today_str(), "pass":"Range","kategori":"Kontakt","moment":"Topp","klubba":"","värde":1,"anteckning":""})
            st.session_state.thin_count += 1
            st.info(f"Topp #{st.session_state.thin_count} idag")
            if st.session_state.thin_count == 5: show_thin_tips()
        if k2.button("➕ Duff"):
            log_and_track({"datum": today_str(), "pass":"Range","kategori":"Kontakt","moment":"Duff","klubba":"","värde":1,"anteckning":""})
            st.session_state.fat_count += 1
            st.info(f"Duff #{st.session_state.fat_count} idag")
            if st.session_state.fat_count == 5: show_fat_tips()

        # Driver misskontroll
        st.subheader("Driver – misskontroll")
        d1, d2, d3 = st.columns(3)
        if d1.button("➕ Slice (driver)"):
            log_and_track({"datum": today_str(), "pass":"Range","kategori":"Driver","moment":"Slice","klubba":"Driver","värde":1,"anteckning":""})
            st.session_state.slice_count += 1
            st.info(f"Driver slice #{st.session_state.slice_count} idag")
            if st.session_state.slice_count >= 3:
                show_slice_tips()
        if d2.button("➕ Hook (driver)"):
            log_and_track({"datum": today_str(), "pass":"Range","kategori":"Driver","moment":"Hook","klubba":"Driver","värde":1,"anteckning":""})
            st.session_state.hook_count += 1
            st.info(f"Driver hook #{st.session_state.hook_count} idag")
            if st.session_state.hook_count >= 3:
                show_hook_tips()
        if d3.button("➕ Neutral (driver)"):
            log_and_track({"datum": today_str(), "pass":"Range","kategori":"Driver","moment":"Neutral","klubba":"Driver","värde":1,"anteckning":""})
            st.success("Loggat: Driver Neutral")

        # Draw/Fade drills (järn & driver)
        st.subheader("Forma bollbanan – Draw/Fade")
        cA, cB, cC, cD = st.columns(4)
        if cA.button("➕ Slå Draw (järn)"):
            log_and_track({"datum": today_str(), "pass":"Range","kategori":"Shape","moment":"Draw (iron)","klubba":"Iron","värde":1,"anteckning":""})
            with st.expander("Enkel draw-drill (järn)"):
                st.markdown("- Sikta klubban rakt, ställ fötterna lite **höger**.\n- Lägg en peg 2–3 m fram, **höger** om målet – starta genom den.\n- Låt händerna **rulla över** genom träffen.")
        if cB.button("➕ Slå Fade (järn)"):
            log_and_track({"datum": today_str(), "pass":"Range","kategori":"Shape","moment":"Fade (iron)","klubba":"Iron","värde":1,"anteckning":""})
            with st.expander("Enkel fade-drill (järn)"):
                st.markdown("- Sikta klubban rakt, ställ fötterna lite **vänster**.\n- Peg 2–3 m fram, **vänster** om mål – starta genom den.\n- **Hold face** genom träffen (lite mindre release).")
        if cC.button("➕ Slå Draw (driver)"):
            log_and_track({"datum": today_str(), "pass":"Range","kategori":"Shape","moment":"Draw (driver)","klubba":"Driver","värde":1,"anteckning":""})
            with st.expander("Enkel draw-drill (driver)"):
                st.markdown("- Boll fram, **hög tee**.\n- Svinga **inifrån** (undvik peggen utanför bakom bollen).\n- Låt händerna rotera igenom (svag draw-känsla).")
        if cD.button("➕ Slå Fade (driver)"):
            log_and_track({"datum": today_str(), "pass":"Range","kategori":"Shape","moment":"Fade (driver)","klubba":"Driver","värde":1,"anteckning":""})
            with st.expander("Enkel fade-drill (driver)"):
                st.markdown("- Boll fram, tee normalt.\n- Svinga något **utifrån-in**.\n- Håll face lite öppet längre (kontrollerad fade).")

        # Snabb carry-inmatning
        st.subheader("Längdkontroll – Snabb Carry")
        left, mid, right = st.columns([2,1,2])
        default_club = st.session_state.get("last_club", "7i")
        default_carry = int(st.session_state.get("last_carry", 150))
        if default_club not in CLUBS:
            default_club = "7i"
        club_index = CLUBS.index(default_club)
        klubba = left.selectbox("Klubba", CLUBS, index=club_index, key="club_sel")
        carry_val = left.number_input("Carry (m)", min_value=0, max_value=400, value=default_carry, step=1, key="carry_input")
        a1, a2, a3, a4 = left.columns(4)
        if a1.button("-5"): st.session_state.carry_input = max(0, st.session_state.carry_input - 5)
        if a2.button("-1"): st.session_state.carry_input = max(0, st.session_state.carry_input - 1)
        if a3.button("+1"): st.session_state.carry_input = min(400, st.session_state.carry_input + 1)
        if a4.button("+5"): st.session_state.carry_input = min(400, st.session_state.carry_input + 5)
        st.session_state.fast_mode = mid.toggle("Upprepa förra", value=st.session_state.get("fast_mode", True))

        def log_carry(sel_club, val):
            row = {"datum": today_str(), "pass":"Range","kategori":"Längdkontroll","moment":"Carry","klubba":sel_club,"värde":int(val),"anteckning":""}
            log_and_track(row)
            st.session_state.last_club = sel_club
            st.session_state.last_carry = int(val)
            st.success(f"Loggat: {sel_club} – {int(val)} m")

        if right.button("➕ Logga carry"):
            log_carry(klubba, st.session_state.carry_input)
        if right.button("⟳ Upprepa förra"):
            log_carry(st.session_state.last_club, st.session_state.last_carry)

    elif pass_typ == "Närspel":
        st.subheader("Chippar")
        c1, c2 = st.columns(2)
        if c1.button("➕ Chip inom 2 m"):
            log_and_track({"datum": today_str(), "pass":"Närspel","kategori":"Chippar","moment":"Inom 2m","klubba":"","värde":1,"anteckning":""})
            st.success("Loggat: Chip inom 2 m")
        if c2.button("➕ Chip utanför 2 m"):
            log_and_track({"datum": today_str(), "pass":"Närspel","kategori":"Chippar","moment":"Utanför 2m","klubba":"","värde":1,"anteckning":""})
            st.info("Loggat: Chip utanför 2 m")

        st.subheader("Pitchar")
        p1, p2 = st.columns(2)
        if p1.button("➕ Pitch inom 5 m/green"):
            log_and_track({"datum": today_str(), "pass":"Närspel","kategori":"Pitchar","moment":"Inom 5m/green","klubba":"","värde":1,"anteckning":""})
            st.success("Loggat: Pitch inom 5 m / green")
        if p2.button("➕ Pitch utanför 5 m"):
            log_and_track({"datum": today_str(), "pass":"Närspel","kategori":"Pitchar","moment":"Utanför 5m","klubba":"","värde":1,"anteckning":""})
            st.info("Loggat: Pitch utanför 5 m")

        st.subheader("Puttning")
        pp1, pp2 = st.columns(2)
        if pp1.button("➕ Kortputt i hål (1–2 m)"):
            log_and_track({"datum": today_str(), "pass":"Närspel","kategori":"Puttning","moment":"Kortputt i hål","klubba":"","värde":1,"anteckning":""})
            st.success("Loggat: Kortputt i hål")
        dist = pp2.number_input("Långputt – snittavstånd kvar (m)", min_value=0.0, max_value=30.0, value=2.0, step=0.1)
        if pp2.button("➕ Logga långputt-snitt"):
            log_and_track({"datum": today_str(), "pass":"Närspel","kategori":"Puttning","moment":"Långputt snitt","klubba":"","värde":dist,"anteckning":""})
            st.info(f"Loggat: Långputt snitt {dist} m")

# -----------------------------
# STATISTIK
# -----------------------------
elif view == "Statistik":
    st.header("📈 Statistik")
    df = df_all.copy()
    if df.empty:
        st.info("Ingen data ännu.")
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
            plt.title("Träffbild per dag"); plt.xlabel("Datum"); plt.ylabel("Antal")
            st.pyplot(fig)

        st.subheader("Kontakt – Topp/Duff")
        kt = df[(df['pass']=="Range") & (df['kategori']=="Kontakt")]
        if not kt.empty:
            kpivot = kt.pivot_table(index='datum', columns='moment', values='värde', aggfunc='sum').fillna(0)
            figk = plt.figure()
            kpivot.plot(kind='bar', ax=plt.gca())
            plt.title("Kontakt per dag"); plt.xlabel("Datum"); plt.ylabel("Antal")
            st.pyplot(figk)

        st.subheader("Driver – Slice/Hook/Neutral per dag")
        dv = df[(df['pass']=="Range") & (df['kategori']=="Driver")]
        if dv.empty:
            st.caption("Ingen driver-data ännu.")
        else:
            dp = dv.pivot_table(index='datum', columns='moment', values='värde', aggfunc='sum').fillna(0)
            st.dataframe(dp, use_container_width=True)
            figd = plt.figure()
            dp.plot(kind='bar', ax=plt.gca())
            plt.title("Driver-missar per dag"); plt.xlabel("Datum"); plt.ylabel("Antal")
            st.pyplot(figd)

        st.subheader("Shape – Draw/Fade försök")
        sh = df[(df['pass']=="Range") & (df['kategori']=="Shape")]
        if not sh.empty:
            shp = sh.pivot_table(index='datum', columns='moment', values='värde', aggfunc='sum').fillna(0)
            st.dataframe(shp, use_container_width=True)
            figs = plt.figure()
            shp.plot(kind='bar', ax=plt.gca())
            plt.title("Draw/Fade försök per dag"); plt.xlabel("Datum"); plt.ylabel("Antal")
            st.pyplot(figs)

        st.subheader("Längdkontroll – Carry per klubba")
        lc = df[(df['pass']=="Range") & (df['kategori']=="Längdkontroll") & (df['moment']=="Carry")]
        lc['värde'] = pd.to_numeric(lc['värde'], errors='coerce')
        lc = lc[lc['värde']>0]
        if lc.empty:
            st.caption("Ingen carry-data ännu.")
        else:
            grp = lc.groupby(['datum','klubba'])['värde'].mean().reset_index()
            st.dataframe(grp)
            for klubba, sub in grp.groupby('klubba'):
                fig2 = plt.figure()
                plt.plot(sub['datum'], sub['värde'], marker='o')
                plt.title(f"Carry över tid – {klubba}")
                plt.xlabel("Datum"); plt.ylabel("Meter")
                st.pyplot(fig2)

# -----------------------------
# VIDEO (auto-drill inkl slice/hook)
# -----------------------------
elif view == "Video":
    st.header("🎥 Videoanalys (prototyp)")
    st.caption("Ladda upp svingvideo, tagga med klubba/vinkel/miss och få drill-förslag direkt.")

    up = st.file_uploader("Ladda upp video (mp4, mov)", type=["mp4","mov"])
    c1, c2 = st.columns(2)
    vinkel = c1.selectbox("Vinkel", ["Face-on (framifrån)", "Down-the-line (bakom)"])
    klubba = c2.selectbox("Klubba", [
        "LW (60deg)","SW (56deg)","GW (52deg)","PW (48deg)",
        "9i","8i","7i","6i","5i","4i","Hybrid 4","Hybrid 3","Tra-5","Tra-3","Driver"
    ], index=12)
    c3, c4 = st.columns(2)
    miljo = c3.selectbox("Miljö", ["Range","Närspel","Bana"])
    miss = c4.selectbox("Miss/Resultat", ["Mitt i", "Tåträff", "Hälträff", "Topp", "Duff", "Slice", "Hook", "Annat"])
    kommentar = st.text_area("Kommentar (valfritt)", placeholder="Känsla, drill, noteringar...")

    if up is not None:
        st.video(up)
        if st.button("💾 Spara video + metadata"):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = os.path.splitext(up.name)[1].lower()
            safe_name = f"swing_{ts}{ext}"
            save_path = os.path.join(VIDEO_DIR, safe_name)
            with open(save_path, "wb") as f:
                f.write(up.read())
            meta = {
                "ts": ts,
                "filnamn": safe_name,
                "storlek_bytes": os.path.getsize(save_path),
                "format": ext.replace(".",""),
                "vinkel": vinkel,
                "klubba": klubba,
                "miljo": miljo,
                "miss": miss,
                "kommentar": kommentar.strip()
            }
            append_video_meta(meta)
            st.success("Sparat!")

            tips_map = {
                "Tåträff": "Stå lite närmare, balans mitt/framfot, armar förlängs. Drill: peg utanför bollen (missas).",
                "Hälträff": "Håll spacing, aningen längre ifrån. Drill: peg innanför bollen (missas).",
                "Topp": "Behåll posture; markkontakt efter bollen. Drill: mynt 3–5 cm efter bollen.",
                "Duff": "Vikt mot framfot; turf på streck framför bollen. Drill: markkontakt efter strecket.",
                "Slice": "Starkare grepp, stäng face, in-to-out, högre tee (driver).",
                "Hook": "Svagare grepp, neutralare path, kontrollerad release; träna liten fade."
            }
            if miss == "Mitt i":
                st.balloons()
                st.success("Bra jobbat! Mitt i. Spara känslan och fortsätt.")
            elif miss in tips_map:
                st.warning(f"Tips för {miss}: {tips_map[miss]}")
            else:
                st.info("Fundera på vad du vill förbättra i videon, lägg en kommentar och koppla till en drill.")

    st.subheader("📚 Dina videos")
    dv = read_videos()
    if dv.empty:
        st.info("Inga videos sparade ännu.")
    else:
        dv = dv.sort_values("ts", ascending=False).reset_index(drop=True)
        st.dataframe(dv, use_container_width=True)
        latest_path = os.path.join(VIDEO_DIR, dv.iloc[0]["filnamn"])
        if os.path.exists(latest_path):
            st.markdown("**Senaste video (förhandsvisning):**")
            with open(latest_path, "rb") as f:
                st.video(f.read())

# -----------------------------
# PROFIL (svinghastighet + skaft + gripbilder)
# -----------------------------
elif view == "Profil":
    st.header("👤 Profil och utrustning")
    profile = read_profile()

    c1, c2 = st.columns(2)
    speed_val = c1.number_input("Svinghastighet (värde)", min_value=10.0, max_value=200.0, value=float(profile.get("swing_speed_value",95)), step=1.0)
    speed_unit = c1.selectbox("Enhet", ["mph","m/s"], index=(0 if profile.get("swing_speed_unit","mph")=="mph" else 1))
    shaft = c2.selectbox("Skaftstyvhet (driver)", ["L","A","R","S","X"], index=["L","A","R","S","X"].index(profile.get("shaft_flex","R")))

    if st.button("💾 Spara profil"):
        new_p = {"swing_speed_value": speed_val, "swing_speed_unit": speed_unit, "shaft_flex": shaft}
        write_profile(new_p)
        st.success("Profil sparad.")

    st.markdown("---")
    st.subheader("Grepp – exempelbilder")
    colg1, colg2 = st.columns(2)
    slice_img = os.path.join(IMG_DIR, "slice_grip.png")
    hook_img = os.path.join(IMG_DIR, "hook_grip.png")
    if os.path.exists(slice_img):
        colg1.image(slice_img, caption="Mot slice: starkare grepp (händer roteras lite åt höger).")
    else:
        colg1.info("Lägg in bild: data/images/slice_grip.png")
    if os.path.exists(hook_img):
        colg2.image(hook_img, caption="Mot hook: svagare grepp (händer roteras lite åt vänster).")
    else:
        colg2.info("Lägg in bild: data/images/hook_grip.png")

    # Live suggestion preview
    target, msg = suggest_shaft(speed_val, speed_unit, shaft)
    st.markdown("---")
    st.subheader("Utrustningsförslag (utifrån dina värden)")
    st.write(f"Rekommenderad flex: **{target}**")
    if msg:
        st.info(msg)

# -----------------------------
# DATA
# -----------------------------
else:
    st.header("📄 Data")
    df_all = read_log()
    st.write("Alla loggade rader. Filen sparas som `data/logg.csv`.")
    st.dataframe(df_all, use_container_width=True)
    st.download_button("⬇️ Ladda ner hela loggen (CSV)",
                       data=df_all.to_csv(index=False).encode("utf-8"),
                       file_name="golf_logg.csv", mime="text/csv")
    st.markdown("---")
    st.write("Video-metadata sparas som `data/videos.csv`. Videofilerna ligger i `data/videos/`.")
