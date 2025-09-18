
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date, datetime
import os, json

st.set_page_config(page_title="Golf Träningslogg", page_icon="⛳", layout="centered")

# Load base CSS
with open("assets/style.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ---------------------------------
# Paths & constants
# ---------------------------------
DATA_DIR = "data"
VIDEO_DIR = os.path.join(DATA_DIR, "videos")
IMG_DIR = os.path.join(DATA_DIR, "images")
ANALYTICS_DIR = os.path.join(DATA_DIR, "trackman")
LOG_PATH = os.path.join(DATA_DIR, "logg.csv")
VIDEO_META = os.path.join(DATA_DIR, "videos.csv")
PROFILE_JSON = os.path.join(DATA_DIR, "profile.json")
os.makedirs(DATA_DIR, exist_ok=True); os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True); os.makedirs(ANALYTICS_DIR, exist_ok=True)

COLUMNS = ["datum", "pass", "kategori", "moment", "klubba", "värde", "anteckning"]
VIDEO_COLUMNS = ["ts","filnamn","storlek_bytes","format","vinkel","klubba","miljo","miss","kommentar"]
CLUBS = ["Driver","Tra-3","Tra-5","Hybrid 3","Hybrid 4","4i","5i","6i","7i","8i","9i","PW (48deg)","GW (52deg)","SW (56deg)","LW (60deg)"]

# ---------------------------------
# Data helpers
# ---------------------------------
def init_log():
    if not os.path.exists(LOG_PATH):
        pd.DataFrame(columns=COLUMNS).to_csv(LOG_PATH, index=False, encoding="utf-8")
    if not os.path.exists(VIDEO_META):
        pd.DataFrame(columns=VIDEO_COLUMNS).to_csv(VIDEO_META, index=False, encoding="utf-8")
    if not os.path.exists(PROFILE_JSON):
        with open(PROFILE_JSON, "w", encoding="utf-8") as f:
            json.dump({
                "swing_speed_value": 95, "swing_speed_unit": "mph", "shaft_flex": "R",
                "hcp": 36, "coach_mode": "Auto", "onboarded": False, "goal":"Balans & träffbild",
                "primary_color":"#1E88E5", "dark_mode": False
            }, f)

def read_log():
    init_log()
    try: df = pd.read_csv(LOG_PATH, encoding="utf-8")
    except Exception: df = pd.DataFrame(columns=COLUMNS)
    for c in COLUMNS:
        if c not in df.columns: df[c] = ""
    return df

def write_log(df): df.to_csv(LOG_PATH, index=False, encoding="utf-8")

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
        return {"swing_speed_value": 95, "swing_speed_unit": "mph", "shaft_flex": "R",
                "hcp":36, "coach_mode":"Auto", "onboarded": False, "goal":"Balans & träffbild",
                "primary_color":"#1E88E5", "dark_mode": False}

def write_profile(p):
    with open(PROFILE_JSON, "w", encoding="utf-8") as f:
        json.dump(p, f)

def today_str(): return date.today().isoformat()

# ---------------------------------
# Coach mode
# ---------------------------------
def resolve_coach_mode(profile: dict) -> str:
    mode = profile.get("coach_mode","Auto")
    if mode != "Auto": return mode
    hcp = float(profile.get("hcp",36))
    return "Enkel" if hcp >= 28 else "Avancerad"

# ---------------------------------
# Glossary
# ---------------------------------
GLOSSARY = {
    "Down The Line": "Kameravinkel bakifrån, parallellt med siktlinjen.",
    "Face On": "Kameravinkel framifrån, mot spelaren.",
    "Angle of Attack": "Träffvinkel uppåt (positiv) eller nedåt (negativ) i grader.",
    "Club Path": "Klubbans svingriktning vid träff (°). Minus = utifrån-in, plus = inifrån-ut.",
    "Face to Path": "Skillnad i grader mellan klubbhuvudets riktning och svingriktningen.",
    "Launch": "Startvinkel (°) på bollen.",
    "Spin": "Bakspinn (varv per minut).",
    "Height": "Maxhöjd (meter).",
    "Handicap": "Spelarens spelhandicap (HCP)."
}
def glossary_widget():
    with st.expander("📘 Ordlista (öppna för förklaringar)"):
        for k, v in GLOSSARY.items():
            st.markdown(f"**{k}** — {v}")

# ---------------------------------
# Theme controls (dark mode + brand color)
# ---------------------------------
def apply_theme(primary_color: str, dark_mode: bool):
    if dark_mode:
        # Inject dark variables to override defaults
        st.markdown(f"""
        <style>
        :root {{
          --primary: {primary_color};
          --bg: #0B1220;
          --bg-2: #111827;
          --text: #E5E7EB;
          --muted: #9CA3AF;
          --card-bg: #0f172a;
          --card-border: #1f2937;
        }}
        html, body, .block-container {{ background-color: var(--bg) !important; color: var(--text) !important; }}
        .stMarkdown, .stText, .stSelectbox, .stNumberInput, .stButton, .stExpander {{ color: var(--text) !important; }}
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <style>
        :root {{ --primary: {primary_color}; }}
        </style>
        """, unsafe_allow_html=True)

# ---------------------------------
# Club logic & metrics + recs (short, same as previous pretty build)
# ---------------------------------
def club_group(klubba: str) -> str:
    if klubba == "Driver": return "driver"
    if "Tra" in klubba: return "fairway"
    if "Hybrid" in klubba: return "hybrid"
    if any(w in klubba for w in ["PW","GW","SW","LW"]): return "wedge"
    return "iron"

def compute_club_metrics_for(df: pd.DataFrame, klubba: str):
    r = df.copy()
    m = {"center":None, "toe":None, "heel":None, "thin":None, "fat":None, "flush":None, "carry_std":None, "slice":None, "hook":None}
    if r.empty: return m
    tb = r[(r["pass"]=="Range") & (r["kategori"]=="Träffbild") & (r["klubba"]==klubba)]
    if not tb.empty:
        tot = len(tb); m["center"] = (tb["moment"]=="Mitt i").sum()/tot
        m["toe"] = (tb["moment"]=="Tåträff").sum()/tot; m["heel"] = (tb["moment"]=="Hälträff").sum()/tot
    kt = r[(r["pass"]=="Range") & (r["kategori"]=="Kontakt") & (r["klubba"]==klubba)]
    if not kt.empty:
        tot = len(kt); m["thin"] = (kt["moment"]=="Topp").sum()/tot; m["fat"] = (kt["moment"]=="Duff").sum()/tot; m["flush"] = (kt["moment"]=="Flush").sum()/tot
    lc = r[(r["pass"]=="Range") & (r["kategori"]=="Längdkontroll") & (r["moment"]=="Carry") & (r["klubba"]==klubba)].copy()
    if not lc.empty:
        lc["värde"] = pd.to_numeric(lc["värde"], errors="coerce")
        m["carry_std"] = float(lc["värde"].dropna().std()) if len(lc)>=3 else None
    if klubba=="Driver":
        dv = r[(r["pass"]=="Range") & (r["kategori"]=="Driver")]
        if not dv.empty:
            tot = len(dv); m["slice"] = (dv["moment"]=="Slice").sum()/tot; m["hook"] = (dv["moment"]=="Hook").sum()/tot
    return m

BENCHMARKS_BASE = {
    "clean_rate": {"Pro":0.65, "Adv":0.50, "Beg":0.35},
    "driver_slice_rate": {"Pro":0.12, "Adv":0.18, "Beg":0.25},
    "driver_hook_rate":  {"Pro":0.12, "Adv":0.18, "Beg":0.25},
    "carry_std_7i": {"Pro":6, "Adv":9, "Beg":13},
    "carry_std_driver": {"Pro":10, "Adv":15, "Beg":22},
}
def hcp_tier(hcp: float):
    if hcp <= 12: return "Pro"
    if hcp <= 28: return "Adv"
    return "Beg"
def targets_for_profile(profile: dict):
    tier = hcp_tier(float(profile.get("hcp",36)))
    t = {k: BENCHMARKS_BASE[k][tier] for k in BENCHMARKS_BASE}
    return tier, t

def recommend_for_club(df: pd.DataFrame, profile: dict, klubba: str, mode: str):
    _, t = targets_for_profile(profile)
    m = compute_club_metrics_for(df, klubba)
    grp = club_group(klubba)
    center_target = t["clean_rate"]
    carry_std_target = t["carry_std_driver"] if grp=="driver" else t["carry_std_7i"]
    items = []
    if m["center"] is not None and m["center"] < center_target:
        items.append({"title":"Mittträff & startlinje","why":"Fler rena träffar minskar spridning och gör längden jämnare.",
                      "how":["Startport 2–3 m framför bollen.","Mynt 3–5 cm efter bollen – landa klubban efter bollen.","2×10 slag genom porten + markkontakt efter bollen."]})
    if (m["thin"] or 0) > 0.25:
        items.append({"title":"Mot toppade slag","why":"Toppar = uppresning i träffen.","how":["Behåll posture.","Träffa marken efter bollen.","5×5 halvslag med fokus på nedslag."]})
    if (m["fat"] or 0) > 0.25:
        items.append({"title":"Mot duffar","why":"Low‑point för tidig.","how":["60/40 vikt fram.","Bröstet över bollen.","Turf efter bollen (mynt‑drill)."]})
    if m["carry_std"] not in [None] and m["carry_std"] > carry_std_target:
        items.append({"title":"Jämnare längdkontroll","why":"Mindre carry‑spridning = bättre klubbval.","how":["Samma bollplacering & tempo (3:1).","Distans‑stege: 5×80%, 5×90%, 5×100%.","Logga carries i appen."]})
    if grp=="driver":
        tier_slice = BENCHMARKS_BASE["driver_slice_rate"][hcp_tier(float(profile.get("hcp",36)))]
        tier_hook  = BENCHMARKS_BASE["driver_hook_rate"][hcp_tier(float(profile.get("hcp",36)))]
        if (m["slice"] or 0) > tier_slice:
            items.append({"title":"Minska slice (driver)","why":"Slice kostar längd & kontroll.",
                          "how": (["Starkare grepp (3–4 knogar), hög tee.","Peg utanför bakom bollen – svinga innanför.","Starta bollen svagt höger, rulla händerna."]
                                  if mode=="Enkel" else ["Face 1–2° stängd mot path.","Path +2–4° in‑to‑out, AoA +2°.","Startlinje svagt höger."])})
        if (m["hook"] or 0) > tier_hook:
            items.append({"title":"Minska hook (driver)","why":"Hook = över‑release, face för stängt.",
                          "how": (["Svagare grepp (1–2 knogar).","Hold face (mindre release).","Starta rakt/ev. vänster."]
                                  if mode=="Enkel" else ["Face nära 0° mot path.","Neutral path (0 till +1°).","Sen release/handle forward."])})

    if grp=="iron":
        items.append({"title":"Forma Draw/Fade (järn)","why":"Shape‑kontroll ger bättre startlinje & greenträffar.",
                      "how": (["Draw: sikta rakt, fötter lite höger, port höger.","Fade: sikta rakt, fötter lite vänster, hold face.","10 bollar per shape – logga."]
                              if mode=="Enkel" else ["Draw: path +2–4°, face 1–2° stängd.","Fade: path −2–4°, face 0–1° öppen.","Port 2–3 m framför för startlinje."])})

    if grp in ["fairway","hybrid"]:
        items.append({"title":"Sweep‑drill","why":"Svepande träff minskar duff/topp.",
                      "how":["Tee lågt (eller ingen).","Sopa marken efter bollen.","10 slag med låg AoA (nära 0)."]})

    if grp=="wedge":
        items.append({"title":"Wedge‑matris (klocksystem)","why":"Fasta längder 30–90 m förenklar besluten.",
                      "how":["Tre baksvings‑längder (8/9/10).","5 slag per längd – logga.","Skriv upp matrisen i appen."]})
        items.append({"title":"Landningspunkt‑drill","why":"Kontrollerad landning ger rätt rull/stopp.",
                      "how":["Välj landnings‑mål 2–3 m in på green.","10 slag – räkna inom 1 m.","Anpassa loft/bounce efter underlag."]})
    if not items: items = [{"title":"Underhåll","why":"Allt ser stabilt ut.","how":["10–15 min valfri drill.","Sätt ett litet mål och logga."]}]
    return items

# ---------------------------------
# TrackMan feedback (clear terms)
# ---------------------------------
def trackman_feedback(data: dict, club: str, mode: str):
    ball_speed = data.get("ball_speed") or 0
    launch = data.get("launch") or 0
    spin = data.get("spin") or 0
    height = data.get("height") or 0
    angle_of_attack = data.get("aoa") or 0
    club_path = data.get("path") or 0
    face_to_path = data.get("face_to_path") or 0
    tips = []
    if club=="Driver":
        if ball_speed>0:
            ideal_launch = 12 if ball_speed<150 else 14 if ball_speed<165 else 15.5
            if launch < ideal_launch-2: tips.append(f"Öka startvinkel: högre tee, bollen längre fram, mer tilt (mål ~{ideal_launch}°).")
            if launch > ideal_launch+3: tips.append(f"Sänk startvinkel: lägre tee/neutral loft (mål ~{ideal_launch}°).")
        if spin>3000: tips.append("Hög spinn: träffa mer uppåt (positiv Angle of Attack) eller minska loft.")
        if 0<spin<1600: tips.append("Väldigt låg spinn: mer loft eller mindre uppåtsving för höjdkontroll.")
        if angle_of_attack<-1: tips.append("Angle of Attack negativ: träna uppåtträff (boll fram, hög tee).")
        if club_path<-2 and face_to_path<-2: tips.append("Utifrån‑in + öppet face → slice‑risk: starkare grepp & inifrån‑sving.")
        if club_path>2 and face_to_path>2: tips.append("Inifrån‑ut + stängt face → hook‑risk: neutralisera face/release.")
    else:
        if launch<14: tips.append("Låg startvinkel: kontrollerad shaft‑lean och ren bollkontakt efter bollen.")
        if launch>22: tips.append("Hög startvinkel: minska dynamiskt loft, träffa nedåt genom bollen.")
        if 0<spin<5000: tips.append("Låg spinn för järn: renare träff & rätt boll/loft.")
        if height<18: tips.append("Låg topphöjd: sikta ~25–35 m med 7i – håll tempo och full finish.")
        if abs(face_to_path)>2.5: tips.append("Stor skillnad mellan face och svingriktning → jobba neutralare face‑till‑path.")
    if not tips: tips = ["Värdena ser rimliga ut. Fortsätt!"]
    if mode=="Avancerad": tips.append("Avancerat: filma från bakom (Down The Line) och framifrån (Face On) och jämför sekvens/release med drillen.")
    return tips

# ---------------------------------
# UI (Header + Sidebar controls)
# ---------------------------------
profile = read_profile()
mode = resolve_coach_mode(profile)
tier, targets = targets_for_profile(profile)

# Branding controls
st.sidebar.subheader("🎨 Utseende")
primary_color = st.sidebar.color_picker("Primärfärg", value=profile.get("primary_color", "#1E88E5"))
dark_mode = st.sidebar.toggle("🌙 Mörkt läge", value=bool(profile.get("dark_mode", False)))
if st.sidebar.button("Spara tema"):
    profile["primary_color"] = primary_color
    profile["dark_mode"] = bool(dark_mode)
    write_profile(profile)
    st.sidebar.success("Tema sparat.")

# Apply theme after reading controls
apply_theme(primary_color, dark_mode)

# Header with logo
st.markdown('<div class="card">', unsafe_allow_html=True)
st.image("assets/logo.png", width=200)
st.markdown('<div class="badge">Golf Träningslogg</div>', unsafe_allow_html=True)
st.markdown("<h3>⛳ Din personliga träningscoach</h3>", unsafe_allow_html=True)
st.markdown('<p class="small">Logga pass, analysera värden och få rekommendationer per klubba.</p>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.sidebar.markdown(f"**Coach-läge:** {mode}  •  **Handicap:** {profile.get('hcp',36)}  •  **Mål-nivå:** {tier}")
view = st.sidebar.radio("Navigera", ["Logga pass","Rekommendationer","TrackMan Analyzer","Benchmark","Profil","Ordlista","Data"])

# ---------------------------------
# Views
# ---------------------------------
def today_str(): return date.today().isoformat()
def reset_daily_counters(): pass  # simple build omits auto counters here

def log_section(title): st.markdown(f'<div class="card"><h4>{title}</h4>', unsafe_allow_html=True)
def end_section(): st.markdown('</div>', unsafe_allow_html=True)

if view=="Logga pass":
    log_section("Välj pass & klubba")
    c1,c2 = st.columns(2)
    pass_typ = c1.selectbox("Träningspass", ["Range","Närspel","Bana"])
    aktiv_klubba = c2.selectbox("Klubba", CLUBS, index=CLUBS.index("7i") if "last_club" not in st.session_state else CLUBS.index(st.session_state.get("last_club","7i")))
    st.session_state["last_club"] = aktiv_klubba
    end_section()

    if pass_typ=="Range":
        log_section("Träffbild")
        c1,c2,c3 = st.columns(3)
        if c1.button("➕ Mitt i"): append_row({"datum": today_str(),"pass":"Range","kategori":"Träffbild","moment":"Mitt i","klubba":aktiv_klubba,"värde":1,"anteckning":""})
        if c2.button("➕ Tåträff"): append_row({"datum": today_str(),"pass":"Range","kategori":"Träffbild","moment":"Tåträff","klubba":aktiv_klubba,"värde":1,"anteckning":""})
        if c3.button("➕ Hälträff"): append_row({"datum": today_str(),"pass":"Range","kategori":"Träffbild","moment":"Hälträff","klubba":aktiv_klubba,"värde":1,"anteckning":""})
        end_section()

        log_section("Kontakt")
        k1,k2,k3 = st.columns(3)
        if k1.button("➕ Topp"): append_row({"datum": today_str(),"pass":"Range","kategori":"Kontakt","moment":"Topp","klubba":aktiv_klubba,"värde":1,"anteckning":""})
        if k2.button("➕ Duff"): append_row({"datum": today_str(),"pass":"Range","kategori":"Kontakt","moment":"Duff","klubba":aktiv_klubba,"värde":1,"anteckning":""})
        if k3.button("✅ Flush (perfekt)"):
            append_row({"datum": today_str(),"pass":"Range","kategori":"Kontakt","moment":"Flush","klubba":aktiv_klubba,"värde":1,"anteckning":""})
            st.success("Flush – snyggt!")
        end_section()

        log_section("Längdkontroll – Snabb carry")
        cL, cR = st.columns([2,1])
        carry_val = cL.number_input("Carry (meter)", min_value=0, max_value=400, value=150, step=1, key="carry_input")
        if cR.button("➕ Logga carry"):
            append_row({"datum": today_str(),"pass":"Range","kategori":"Längdkontroll","moment":"Carry","klubba":aktiv_klubba,"värde":int(carry_val),"anteckning":""})
        end_section()

elif view=="Rekommendationer":
    aktiv_klubba = st.selectbox("Välj klubba", CLUBS, index=CLUBS.index("7i") if "last_club" not in st.session_state else CLUBS.index(st.session_state.get("last_club","7i")))
    st.session_state["last_club"] = aktiv_klubba
    log_section(f"Fokus för {aktiv_klubba}")
    recs = recommend_for_club(read_log(), read_profile(), aktiv_klubba, resolve_coach_mode(read_profile()))
    for r in recs:
        with st.expander(f"• {r['title']}"):
            st.write(f"**Varför:** {r['why']}")
            st.markdown("\n".join([f"- {step}" for step in r["how"]]))
    end_section()

elif view=="TrackMan Analyzer":
    log_section("Analys av launch monitor-data")
    st.caption("Ladda upp en skärmdump (valfritt). Fyll i siffrorna för att få tips.")
    img = st.file_uploader("Bild (jpg/png)", type=["jpg","jpeg","png"])
    if img is not None: st.image(img, caption="Uppladdad bild", use_column_width=True)
    klubba = st.selectbox("Klubba", ["Driver","7i","8i","9i","6i","5i","4i"], index=1)
    col1,col2,col3 = st.columns(3)
    ball_speed = col1.number_input("Bollhastighet (mph)", min_value=0.0, max_value=220.0, step=0.1)
    launch = col2.number_input("Startvinkel (°)", min_value=0.0, max_value=30.0, step=0.1)
    spin = col3.number_input("Bakspinn (rpm)", min_value=0.0, max_value=12000.0, step=10.0)
    col4,col5,col6 = st.columns(3)
    height = col4.number_input("Topp-höjd (m)", min_value=0.0, max_value=80.0, step=0.1)
    aoa = col5.number_input("Angle of Attack (°)", min_value=-10.0, max_value=10.0, step=0.1)
    face_to_path = col6.number_input("Face to Path (°)", min_value=-10.0, max_value=10.0, step=0.1)
    club_path = st.number_input("Svingriktning – Club Path (°)", min_value=-10.0, max_value=10.0, step=0.1)
    if st.button("🔍 Analysera & spara"):
        saved_name = None
        if img is not None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = os.path.splitext(img.name)[1].lower()
            saved_name = f"tm_{ts}{ext}"
            with open(os.path.join(ANALYTICS_DIR, saved_name), "wb") as f:
                f.write(img.read())
        data = {"ball_speed":ball_speed,"launch":launch,"spin":spin,"height":height,"aoa":aoa,"face_to_path":face_to_path,"path":club_path}
        tips = trackman_feedback(data, klubba, resolve_coach_mode(read_profile()))
        st.success("Analys klar. Här är dina tips:")
        for t in tips: st.write("• " + t)
    end_section()
    glossary_widget()

elif view=="Benchmark":
    log_section("Jämförelse mot mål")
    df = read_log()
    if df.empty:
        st.info("Logga några pass först.")
    else:
        tb = df[(df["pass"]=="Range") & (df["kategori"]=="Träffbild")]
        clean = (tb["moment"]=="Mitt i").sum(); tot = len(tb)
        clean_rate = None if tot==0 else clean/tot
        st.metric("Rena träffar", f"{0 if clean_rate is None else int(clean_rate*100)}%")
    end_section()

elif view=="Profil":
    p = read_profile()
    log_section("Profil & mål")
    c0,c1,c2 = st.columns(3)
    hcp_val = c0.number_input("Handicap (0–54)", 0.0, 54.0, float(p.get("hcp",36.0)), 0.1)
    speed_val = c1.number_input("Svinghastighet", 10.0, 200.0, float(p.get("swing_speed_value",95)), 1.0)
    speed_unit = c1.selectbox("Enhet", ["mph","m/s"], index=(0 if p.get("swing_speed_unit","mph")=="mph" else 1))
    shaft = c2.selectbox("Skaftstyvhet (driver)", ["L","A","R","S","X"], index=["L","A","R","S","X"].index(p.get("shaft_flex","R")))
    coach_mode = st.selectbox("Coach-läge", ["Auto","Enkel","Avancerad"], index=["Auto","Enkel","Avancerad"].index(p.get("coach_mode","Auto")))
    goal = st.selectbox("Mål", ["Balans & träffbild","Mindre slice/hook","Bättre närspel","Längre med driver"], index=["Balans & träffbild","Mindre slice/hook","Bättre närspel","Längre med driver"].index(p.get("goal","Balans & träffbild")))
    if st.button("💾 Spara profil"):
        p.update({"swing_speed_value": speed_val, "swing_speed_unit": speed_unit, "shaft_flex": shaft,
                  "hcp": hcp_val, "coach_mode": coach_mode, "onboarded": True, "goal": goal,
                  "primary_color": st.session_state.get("primary_color", p.get("primary_color","#1E88E5")),
                  "dark_mode": st.session_state.get("dark_mode", p.get("dark_mode", False))})
        write_profile(p); st.success("Profil sparad!")
    end_section()

elif view=="Ordlista":
    glossary_widget()

else:
    log_section("Loggdata")
    st.dataframe(read_log(), use_container_width=True)
    st.download_button("⬇️ Exportera CSV", data=read_log().to_csv(index=False).encode("utf-8"), file_name="golf_logg.csv", mime="text/csv")
    end_section()
