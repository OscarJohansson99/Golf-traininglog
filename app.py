
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date, datetime
import os, json

st.set_page_config(page_title="Golf Träningslogg", page_icon="⛳", layout="centered")

# -----------------------------
# Paths & constants
# -----------------------------
DATA_DIR = "data"
VIDEO_DIR = os.path.join(DATA_DIR, "videos")
IMG_DIR = os.path.join(DATA_DIR, "images")
ANALYTICS_DIR = os.path.join(DATA_DIR, "trackman")
LOG_PATH = os.path.join(DATA_DIR, "logg.csv")
VIDEO_META = os.path.join(DATA_DIR, "videos.csv")
PROFILE_JSON = os.path.join(DATA_DIR, "profile.json")
os.makedirs(DATA_DIR, exist_ok=True); os.makedirs(VIDEO_DIR, exist_ok=True); os.makedirs(IMG_DIR, exist_ok=True); os.makedirs(ANALYTICS_DIR, exist_ok=True)

COLUMNS = ["datum", "pass", "kategori", "moment", "klubba", "värde", "anteckning"]
VIDEO_COLUMNS = ["ts","filnamn","storlek_bytes","format","vinkel","klubba","miljo","miss","kommentar"]
CLUBS = ["LW (60deg)","SW (56deg)","GW (52deg)","PW (48deg)","9i","8i","7i","6i","5i","4i","Hybrid 4","Hybrid 3","Tra-5","Tra-3","Driver"]

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
            json.dump({"swing_speed_value": 95, "swing_speed_unit": "mph", "shaft_flex": "R",
                       "hcp": 36, "coach_mode": "Auto", "onboarded": False, "goal":"Balans & träffbild"}, f)

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

def read_profile():
    init_log()
    try:
        with open(PROFILE_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"swing_speed_value": 95, "swing_speed_unit": "mph", "shaft_flex": "R", "hcp":36, "coach_mode":"Auto", "onboarded": False, "goal":"Balans & träffbild"}

def write_profile(p):
    with open(PROFILE_JSON, "w", encoding="utf-8") as f:
        json.dump(p, f)

def today_str():
    return date.today().isoformat()

# -----------------------------
# Coach mode
# -----------------------------
def resolve_coach_mode(profile: dict) -> str:
    mode = profile.get("coach_mode","Auto")
    if mode != "Auto": return mode
    hcp = float(profile.get("hcp",36))
    return "Enkel" if hcp >= 28 else "Avancerad"

# -----------------------------
# Session state
# -----------------------------
def ss_get(k, v):
    if k not in st.session_state: st.session_state[k] = v
    return st.session_state[k]

for k, v in [
    ("toe_count",0), ("heel_count",0), ("thin_count",0), ("fat_count",0),
    ("slice_count",0), ("hook_count",0), ("last_club","7i"), ("last_carry",150),
    ("pass_active",False), ("pass_rows",[]), ("pass_started_at", None),
    ("counter_date", today_str())
]:
    ss_get(k, v)

def reset_daily_counters():
    if st.session_state.counter_date != today_str():
        st.session_state.counter_date = today_str()
        for k in ["toe_count","heel_count","thin_count","fat_count","slice_count","hook_count"]:
            st.session_state[k] = 0

# -----------------------------
# Coach tips (levelled)
# -----------------------------
def show_slice_tips(mode="Enkel"):
    st.toast("Driver slice – öppna drillen nedan.", icon="⚠️")
    with st.expander("Drill mot slice" + (" (enkel)" if mode=="Enkel" else " (avancerad)")):
        img_path = os.path.join(IMG_DIR, "slice_grip.png")
        if os.path.exists(img_path): st.image(img_path, caption="Starkare grepp – rotera händerna lite åt höger.")
        if mode=="Enkel":
            st.markdown("- **Grepp:** vrid händerna lite åt **höger** (3–4 knogar).\n- **Tee högt**, slå **uppåt**.\n- Lägg en peg **utanför** bakom bollen – svinga **innanför** peggen (inifrån).")
        else:
            st.markdown("- **Face/Path:** sikta på face ~1–2° stängd mot path.\n- **Startlinje:** svagt höger om mål.\n- **Setup:** boll fram, axlar lätt höger, hög tee.\n- **Känsla:** högerhand trycker, klubban stänger efter träff.")

def show_hook_tips(mode="Enkel"):
    st.toast("Driver hook – öppna drillen nedan.", icon="⚠️")
    with st.expander("Drill mot hook" + (" (enkel)" if mode=="Enkel" else " (avancerad)")):
        img_path = os.path.join(IMG_DIR, "hook_grip.png")
        if os.path.exists(img_path): st.image(img_path, caption="Svagare grepp – rotera händerna lite åt vänster.")
        if mode=="Enkel":
            st.markdown("- **Grepp:** vrid händerna lite **vänster** (1–2 knogar).\n- Starta bollen **rakt/ev. vänster**.\n- **Hold face:** låt klubban **inte** stänga lika mycket.")
        else:
            st.markdown("- **Face/Path:** håll face nära 0° mot path.\n- **Path:** neutralare (mindre inifrån).\n- **Release:** sen/“hold”, handle forward lite genom träffen.")

# -----------------------------
# Benchmarks (scaled by HCP tier)
# -----------------------------
BENCHMARKS_BASE = {
    "clean_rate": {"Pro":0.65, "Adv":0.50, "Beg":0.35},
    "driver_slice_rate": {"Pro":0.12, "Adv":0.18, "Beg":0.25},
    "driver_hook_rate":  {"Pro":0.12, "Adv":0.18, "Beg":0.25},
    "carry_std_7i": {"Pro":6, "Adv":9, "Beg":13},
    "carry_std_driver": {"Pro":10, "Adv":15, "Beg":22},
    "chip_within2_rate": {"Pro":0.60, "Adv":0.45, "Beg":0.30},
    "short_putt_make": {"Pro":0.90, "Adv":0.80, "Beg":0.60}
}
def hcp_tier(hcp: float):
    if hcp <= 12: return "Pro"
    if hcp <= 28: return "Adv"
    return "Beg"
def targets_for_profile(profile: dict):
    tier = hcp_tier(float(profile.get("hcp",36)))
    t = {k: BENCHMARKS_BASE[k][tier] for k in BENCHMARKS_BASE}
    return tier, t

def compute_metrics(df: pd.DataFrame):
    res = {"clean_rate":None,"driver_slice_rate":None,"driver_hook_rate":None,
           "carry_std_7i":None,"carry_std_driver":None,"short_putt_make":None,"chip_within2_rate":None}
    if df.empty: return res
    tb = df[(df["pass"]=="Range") & (df["kategori"]=="Träffbild")]
    if not tb.empty: res["clean_rate"] = (tb["moment"]=="Mitt i").sum()/len(tb)
    dv = df[(df["pass"]=="Range") & (df["kategori"]=="Driver")]
    if not dv.empty:
        res["driver_slice_rate"] = (dv["moment"]=="Slice").sum()/len(dv)
        res["driver_hook_rate"]  = (dv["moment"]=="Hook").sum()/len(dv)
    lc = df[(df["pass"]=="Range") & (df["kategori"]=="Längdkontroll") & (df["moment"]=="Carry")].copy()
    if not lc.empty:
        lc["värde"] = pd.to_numeric(lc["värde"], errors="coerce")
        c7 = lc[lc["klubba"]=="7i"]["värde"].dropna()
        cd = lc[lc["klubba"]=="Driver"]["värde"].dropna()
        res["carry_std_7i"] = float(c7.std()) if len(c7)>=3 else None
        res["carry_std_driver"] = float(cd.std()) if len(cd)>=3 else None
    ch = df[(df["pass"]=="Närspel") & (df["kategori"]=="Chippar")]
    if not ch.empty: res["chip_within2_rate"] = (ch["moment"]=="Inom 2m").sum()/len(ch)
    pt = df[(df["kategori"]=="Puttning")]
    if not pt.empty:
        makes = (pt["moment"]=="Kortputt i hål").sum()
        res["short_putt_make"] = None if makes==0 else 1.0
    return res

# -----------------------------
# Auto-pass generator (enkelt)
# -----------------------------
def recommend_next_session(df: pd.DataFrame, profile: dict):
    m = compute_metrics(df)
    tier, t = targets_for_profile(profile)
    items = []
    # välj största gap
    if m["clean_rate"] is None or m["clean_rate"] < t["clean_rate"]:
        items.append(("Träffbild", "10 min mittträff: startport + mynt 3–5 cm efter bollen"))
    if m["driver_slice_rate"] not in [None] and m["driver_slice_rate"] > t["driver_slice_rate"]:
        items.append(("Driver slice", "10 min: starkare grepp, peg utanför bakom (inifrån)"))
    if m["driver_hook_rate"] not in [None] and m["driver_hook_rate"] > t["driver_hook_rate"]:
        items.append(("Driver hook", "10 min: svagare grepp, hold face, neutral path"))
    if m["carry_std_7i"] not in [None] and m["carry_std_7i"] > t["carry_std_7i"]:
        items.append(("7i-carry spridning", "10 min: samma bollplacering + tempo-metronom"))
    if m["chip_within2_rate"] is None or m["chip_within2_rate"] < t["chip_within2_rate"]:
        items.append(("Chip inom 2 m", "10 min: landningspunkt, 10x—räkna inom 2 m"))
    if not items:
        items = [("Underhåll", "Valfritt pass 30 min – repetera styrkor")]
    return items[:3]

# -----------------------------
# TrackMan Analyzer (form + bild)
# -----------------------------
def trackman_feedback(data: dict, club: str, mode: str):
    bs = data.get("ball_speed") or 0
    launch = data.get("launch") or 0
    spin = data.get("spin") or 0
    h = data.get("height") or 0
    aoa = data.get("aoa") or 0
    path = data.get("path") or 0
    f2p = data.get("face_to_path") or 0

    tips = []
    if club == "Driver":
        # mycket grova riktvärden
        if bs > 0:
            ideal_launch = 12 if bs < 150 else 14 if bs < 165 else 15.5
            if launch < ideal_launch-2: tips.append(f"Öka launch: högre tee, boll längre fram, mer tilt (mål ~{ideal_launch}°).")
            if launch > ideal_launch+3: tips.append(f"Sänk launch något: lägre tee/neutral loft (mål ~{ideal_launch}°).")
        if spin > 0 and spin > 3000: tips.append("För hög spinn: träffa mer uppåt (+AoA), minska loft/mer fram flytt av vikt.")
        if spin > 0 and spin < 1600: tips.append("Väldigt låg spinn: risk för dippar – mer loft eller mindre uppåt‑träff.")
        if aoa < -1: tips.append("AoA negativ: träna slå **uppåt** på bollen (boll längre fram, hög tee).")
        if path > 2 and f2p > 2: tips.append("Path inifrån + face stängd → risk hook; neutralisera face/release.")
        if path < -2 and f2p < -2: tips.append("Path utifrån + face öppen → risk slice; starkare grepp, in-to-out.")
    else:  # järn
        if launch < 14: tips.append("Låg launch: mer shaft lean kontrollerat, ren bollkontakt efter bollen.")
        if launch > 22: tips.append("Hög launch: kolla loft/dynamic loft, träffa nedåt genom bollen.")
        if spin > 0 and spin < 5000: tips.append("Låg spinn för järn: renare träff & rätt bollval/loft.")
        if h < 18: tips.append("Låg topphöjd: sikta ~25–35 m med 7i – håll tempo och full finish.")
        if abs(f2p) > 2.5: tips.append("Stor face/path-diff → jobba mot neutralare face till path.")

    if not tips:
        tips = ["Värdena ser rimliga ut för denna klubba. Fortsätt!"]
    if mode == "Avancerad":
        tips.append("Avancerat: filma DTL + FO och jämför release/sekvens med drillen.")
    return tips

# -----------------------------
# UI
# -----------------------------
st.title("⛳ Golf Träningslogg")

df_all = read_log()
profile = read_profile()
mode = resolve_coach_mode(profile)
tier, targets = targets_for_profile(profile)

# Onboarding
if not profile.get("onboarded", False):
    st.header("🎯 Välkommen! Snabb start")
    c0,c1,c2 = st.columns(3)
    hcp_val = c0.number_input("HCP (0–54)", 0.0, 54.0, float(profile.get("hcp",36.0)), 0.1)
    coach_mode = st.selectbox("Coach-läge", ["Auto","Enkel","Avancerad"], index=["Auto","Enkel","Avancerad"].index(profile.get("coach_mode","Auto")))
    goal = st.selectbox("Ditt mål just nu", ["Balans & träffbild","Mindre slice/hook","Bättre närspel","Längre med driver"])
    if st.button("✅ Klart – spara & börja"):
        profile.update({"hcp": hcp_val, "coach_mode": coach_mode, "goal": goal, "onboarded": True})
        write_profile(profile)
        st.rerun()

st.sidebar.markdown(f"**Coach-läge:** {mode}  •  **HCP:** {profile.get('hcp',36)}  •  **Målnivå:** {tier}")
view = st.sidebar.radio("Välj vy", ["Logga pass","TrackMan Analyzer","Benchmark","Profil","Data"])

def log_and_track(row):
    append_row(row)
    if st.session_state.pass_active:
        st.session_state.pass_rows.append(row)

# LOGGA PASS (kortare version – fokus på Analyzer & Benchmark i denna build)
if view == "Logga pass":
    reset_daily_counters()
    st.subheader("Välj träningspass & klubba")
    pass_typ = st.selectbox("Träningspass", ["Range","Närspel","Bana"])
    aktiv_klubba = st.selectbox("Klubba för detta pass", CLUBS, index=CLUBS.index(st.session_state.get("last_club","7i")))
    st.session_state.last_club = aktiv_klubba

    if pass_typ == "Range":
        st.markdown("### Träffbild")
        c1,c2,c3 = st.columns(3)
        if c1.button("➕ Mitt i"): log_and_track({"datum": today_str(),"pass":"Range","kategori":"Träffbild","moment":"Mitt i","klubba":aktiv_klubba,"värde":1,"anteckning":""})
        if c2.button("➕ Tåträff"):
            log_and_track({"datum": today_str(),"pass":"Range","kategori":"Träffbild","moment":"Tåträff","klubba":aktiv_klubba,"värde":1,"anteckning":""})
            st.session_state.toe_count += 1
            if st.session_state.toe_count == 5: st.toast("Tåträff – stå lite närmare, balans mitt/framfot.", icon="⚠️")
        if c3.button("➕ Hälträff"):
            log_and_track({"datum": today_str(),"pass":"Range","kategori":"Träffbild","moment":"Hälträff","klubba":aktiv_klubba,"värde":1,"anteckning":""})
            st.session_state.heel_count += 1
            if st.session_state.heel_count == 5: st.toast("Hälträff – håll spacing, aningen längre ifrån.", icon="⚠️")

        st.markdown("### Kontakt")
        k1,k2,k3 = st.columns(3)
        if k1.button("➕ Topp"):
            log_and_track({"datum": today_str(),"pass":"Range","kategori":"Kontakt","moment":"Topp","klubba":aktiv_klubba,"värde":1,"anteckning":""})
            st.session_state.thin_count += 1
        if k2.button("➕ Duff"):
            log_and_track({"datum": today_str(),"pass":"Range","kategori":"Kontakt","moment":"Duff","klubba":aktiv_klubba,"värde":1,"anteckning":""})
            st.session_state.fat_count += 1
        if k3.button("✅ Flush (perfekt)"):
            log_and_track({"datum": today_str(),"pass":"Range","kategori":"Kontakt","moment":"Flush","klubba":aktiv_klubba,"värde":1,"anteckning":""})
            st.success("Flush – snyggt!")

        # Snabb carry
        st.markdown("### Längdkontroll – Snabb Carry")
        left, right = st.columns(2)
        carry_val = left.number_input("Carry (m)", min_value=0, max_value=400, value=int(st.session_state.get("last_carry",150)), step=1, key="carry_input")
        if right.button("➕ Logga carry"):
            log_and_track({"datum": today_str(),"pass":"Range","kategori":"Längdkontroll","moment":"Carry","klubba":aktiv_klubba,"värde":int(carry_val),"anteckning":""})
            st.session_state.last_carry = int(carry_val)

        # Rekommenderat nästa pass (direkt, små “chips”)
        st.markdown("---")
        st.subheader("🎯 Rek. nästa pass (auto)")
        for titel, beskrivning in recommend_next_session(read_log(), read_profile()):
            st.write(f"- **{titel}** – {beskrivning}")

# TRACKMAN ANALYZER
elif view == "TrackMan Analyzer":
    st.header("📸 TrackMan / GC-Data – få feedback")
    st.caption("Ladda upp en skärmdump och fyll i siffrorna nedan (snabbt). Appen sparar bilden och ger tips.")
    img = st.file_uploader("Ladda upp bild (jpg/png)", type=["jpg","jpeg","png"])
    if img is not None:
        st.image(img, caption="Uppladdad bild", use_column_width=True)
    klubba = st.selectbox("Klubba", ["Driver","7i","8i","9i","6i","5i","4i"] , index=1)
    col1,col2,col3 = st.columns(3)
    ball_speed = col1.number_input("Ball Speed (mph)", min_value=0.0, max_value=220.0, step=0.1)
    launch = col2.number_input("Launch (°)", min_value=0.0, max_value=30.0, step=0.1)
    spin = col3.number_input("Spin (rpm)", min_value=0.0, max_value=12000.0, step=10.0)
    col4,col5,col6 = st.columns(3)
    height = col4.number_input("Height (m)", min_value=0.0, max_value=80.0, step=0.1)
    aoa = col5.number_input("AoA (°)", min_value=-10.0, max_value=10.0, step=0.1)
    face_to_path = col6.number_input("Face-to-Path (°)", min_value=-10.0, max_value=10.0, step=0.1)
    path = st.number_input("Club Path (°)", min_value=-10.0, max_value=10.0, step=0.1)

    if st.button("🔍 Analysera & spara"):
        # spara bild om finns
        saved_name = None
        if img is not None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = os.path.splitext(img.name)[1].lower()
            saved_name = f"tm_{ts}{ext}"
            with open(os.path.join(ANALYTICS_DIR, saved_name), "wb") as f:
                f.write(img.read())
        # sammanställ och tips
        data = {"ball_speed":ball_speed,"launch":launch,"spin":spin,"height":height,"aoa":aoa,"face_to_path":face_to_path,"path":path}
        tips = trackman_feedback(data, klubba, resolve_coach_mode(read_profile()))
        st.success("Analys klar. Här är dina tips:")
        for t in tips:
            st.write("• " + t)
        # logga en rad för carry/launch om angivet
        if klubba and launch>0:
            append_row({"datum": today_str(), "pass":"Range","kategori":"LM","moment":f"{klubba} launch/spin","klubba":klubba,"värde":launch,"anteckning":f"spin {int(spin)} rpm; bs {ball_speed} mph; img {saved_name or ''}"})
        st.balloons()

    # Visa senaste analyser
    st.markdown("### Dina senaste analyser")
    files = [f for f in os.listdir(ANALYTICS_DIR) if f.lower().endswith((".jpg",".jpeg",".png"))]
    files = sorted(files)[-3:][::-1]
    if files:
        for f in files:
            st.image(os.path.join(ANALYTICS_DIR, f), caption=f)

# BENCHMARK
elif view == "Benchmark":
    st.header("🎯 Benchmark mot mål")
    df = df_all.copy()
    tier, t = targets_for_profile(profile)
    if df.empty:
        st.info("Logga några pass först.")
    else:
        m = compute_metrics(df)
        rows = []
        def fmt_pct(x): return "—" if x is None else f"{round(100*x)}%"
        rows.append(["Rena träffar", fmt_pct(m["clean_rate"]), f"{round(100*t['clean_rate'])}%"])
        rows.append(["Driver slice", fmt_pct(m["driver_slice_rate"]), f"{round(100*t['driver_slice_rate'])}% (lägre bättre)"])
        rows.append(["Driver hook", fmt_pct(m["driver_hook_rate"]), f"{round(100*t['driver_hook_rate'])}% (lägre bättre)"])
        rows.append(["7i spridning carry (m)", "—" if m["carry_std_7i"] is None else round(m["carry_std_7i"],1), t["carry_std_7i"]])
        rows.append(["Driver spridning carry (m)", "—" if m["carry_std_driver"] is None else round(m["carry_std_driver"],1), t["carry_std_driver"]])
        rows.append(["Chip inom 2 m", fmt_pct(m["chip_within2_rate"]), f"{round(100*t['chip_within2_rate'])}%"])
        rows.append(["Kortputt i hål", fmt_pct(m["short_putt_make"]), f"{round(100*t['short_putt_make'])}%"])
        st.dataframe(pd.DataFrame(rows, columns=["Nyckeltal","Du","Mål"]), use_container_width=True)

# PROFIL
elif view == "Profil":
    st.header("👤 Profil & mål")
    p = profile
    c0,c1,c2 = st.columns(3)
    hcp_val = c0.number_input("HCP (0–54)", 0.0, 54.0, float(p.get("hcp",36.0)), 0.1)
    speed_val = c1.number_input("Svinghastighet", 10.0, 200.0, float(p.get("swing_speed_value",95)), 1.0)
    speed_unit = c1.selectbox("Enhet", ["mph","m/s"], index=(0 if p.get("swing_speed_unit","mph")=="mph" else 1))
    shaft = c2.selectbox("Skaftstyvhet (driver)", ["L","A","R","S","X"], index=["L","A","R","S","X"].index(p.get("shaft_flex","R")))
    coach_mode = st.selectbox("Coach-läge", ["Auto","Enkel","Avancerad"], index=["Auto","Enkel","Avancerad"].index(p.get("coach_mode","Auto")))
    goal = st.selectbox("Mål", ["Balans & träffbild","Mindre slice/hook","Bättre närspel","Längre med driver"], index=["Balans & träffbild","Mindre slice/hook","Bättre närspel","Längre med driver"].index(p.get("goal","Balans & träffbild")))
    if st.button("💾 Spara profil"):
        write_profile({"swing_speed_value": speed_val, "swing_speed_unit": speed_unit, "shaft_flex": shaft, "hcp": hcp_val, "coach_mode": coach_mode, "onboarded": True, "goal": goal})
        st.success("Profil sparad!")
    st.info(f"Aktiverat coach-läge nu: **{resolve_coach_mode(read_profile())}**")
else:
    st.header("📄 Data")
    st.dataframe(df_all, use_container_width=True)
    st.download_button("⬇️ Exportera CSV", data=df_all.to_csv(index=False).encode("utf-8"),
                       file_name="golf_logg.csv", mime="text/csv")
