import json
import os
import sys
import subprocess
import csv
from datetime import datetime
import streamlit as st

BASE   = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "config.json")
LOG    = os.path.join(BASE, "logs", "email_log.csv")
OWNER  = "jasmeet27ghotra@gmail.com"

st.set_page_config(page_title="Weather Bot", page_icon="🌤️", layout="wide")

st.markdown("""
<style>
  /* Global */
  [data-testid="stAppViewContainer"] { background: #0f172a; }
  [data-testid="stSidebar"] { background: #1e293b !important; border-right: 1px solid #334155; }
  [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
  h1,h2,h3 { color: #f1f5f9 !important; }
  p, label, .stMarkdown { color: #cbd5e1 !important; }

  /* Cards */
  [data-testid="stExpander"] {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 12px !important;
    margin-bottom: 8px !important;
  }
  [data-testid="stExpander"] summary { color: #f1f5f9 !important; font-weight: 600; }

  /* Metrics */
  [data-testid="stMetric"] {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 16px !important;
  }
  [data-testid="stMetricValue"] { color: #38bdf8 !important; font-size: 2rem !important; }
  [data-testid="stMetricLabel"] { color: #94a3b8 !important; }

  /* Buttons */
  .stButton > button {
    background: linear-gradient(135deg, #0ea5e9, #6366f1) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: opacity 0.2s !important;
  }
  .stButton > button:hover { opacity: 0.85 !important; }

  /* Inputs */
  .stTextInput input, .stSelectbox select, .stMultiSelect [data-baseweb="select"] {
    background: #0f172a !important;
    border: 1px solid #334155 !important;
    color: #f1f5f9 !important;
    border-radius: 8px !important;
  }

  /* Divider */
  hr { border-color: #334155 !important; }

  /* Dataframe */
  [data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

  /* Success/Error */
  [data-testid="stAlert"] { border-radius: 10px !important; }

  /* Radio sidebar */
  [data-testid="stSidebar"] .stRadio label {
    padding: 8px 12px !important;
    border-radius: 8px !important;
    margin: 2px 0 !important;
    display: block !important;
  }
  [data-testid="stSidebar"] .stRadio label:hover { background: #334155 !important; }
</style>
""", unsafe_allow_html=True)

# ── password gate ─────────────────────────────────────────────────────────────
def check_password():
    correct = st.secrets.get("APP_PASSWORD", "weatherbot123")
    if st.session_state.get("authenticated"):
        return True
    st.markdown("""
    <div style="max-width:400px;margin:80px auto;text-align:center;">
      <div style="font-size:64px;margin-bottom:8px;">🌤️</div>
      <h1 style="color:#f1f5f9;margin-bottom:4px;">Weather Bot</h1>
      <p style="color:#64748b;margin-bottom:32px;">Daily weather briefing dashboard</p>
    </div>""", unsafe_allow_html=True)
    col = st.columns([1,2,1])[1]
    with col:
        with st.form("login"):
            pw = st.text_input("Password", type="password", placeholder="Enter password...")
            if st.form_submit_button("Login →", use_container_width=True):
                if pw == correct:
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Incorrect password")
    return False

if not check_password():
    st.stop()

# ── helpers ──────────────────────────────────────────────────────────────────
def load_config():
    with open(CONFIG) as f:
        return json.load(f)

def github_put(path, content_str, message):
    import base64, requests as req
    token = st.secrets.get("GITHUB_TOKEN", "")
    if not token:
        return False
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    api_url = f"https://api.github.com/repos/jasmeet-dev/weather-bot/contents/{path}"
    r = req.get(api_url, headers=headers)
    sha = r.json().get("sha", "")
    payload = {
        "message": message,
        "content": base64.b64encode(content_str.encode()).decode(),
        "sha": sha
    }
    resp = req.put(api_url, json=payload, headers=headers)
    return resp.status_code in (200, 201)

def save_config(cfg):
    content = json.dumps(cfg, indent=2)
    if github_put("config.json", content, "GUI: update config.json"):
        st.success("✅ Config saved and committed to GitHub!")
    else:
        with open(CONFIG, "w") as f:
            f.write(content)
        st.success("Config saved locally!")

def commit_log():
    if not os.path.exists(LOG):
        return
    with open(LOG) as f:
        content = f.read()
    github_put("logs/email_log.csv", content, f"📧 GUI log: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

def run_bot(manual=True):
    env = os.environ.copy()
    if manual:
        env["MANUAL_RUN"] = "1"
    result = subprocess.run(
        ["python3", os.path.join(BASE, "weather_bot.py")],
        capture_output=True, text=True, env=env
    )
    return result.stdout, result.stderr

# ── sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("""
<div style="text-align:center;padding:20px 0 16px 0;">
  <div style="font-size:48px;">🌤️</div>
  <div style="font-size:20px;font-weight:800;color:#f1f5f9;margin-top:4px;">Weather Bot</div>
  <div style="font-size:12px;color:#64748b;margin-top:2px;">Daily briefing dashboard</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.divider()
page = st.sidebar.radio("Navigation", ["📋 Recipients", "🏙️ Cities", "▶️ Run / Test", "📊 Logs"],
                        label_visibility="collapsed")

cfg = load_config()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — RECIPIENTS
# ══════════════════════════════════════════════════════════════════════════════
if page == "📋 Recipients":
    st.markdown("""<div style="background:linear-gradient(135deg,#1e293b,#0f2744);border-radius:16px;
    padding:24px 28px;margin-bottom:24px;border:1px solid #334155;">
    <h2 style="margin:0;color:#f1f5f9;">📋 Recipients</h2>
    <p style="margin:6px 0 0 0;color:#64748b;">Manage who receives the daily weather email.</p>
    </div>""", unsafe_allow_html=True)

    # Pause / Resume all
    col_all1, col_all2 = st.columns(2)
    if col_all1.button("⏸️ Pause ALL emails", use_container_width=True):
        for r in cfg["recipients"]:
            r["active"] = False
        save_config(cfg)
        st.rerun()
    if col_all2.button("▶️ Resume ALL emails", use_container_width=True):
        for r in cfg["recipients"]:
            r["active"] = True
        save_config(cfg)
        st.rerun()
    st.divider()

    city_names = list(cfg["cities"].keys())
    hours      = list(range(6, 13))   # 6 AM – 12 PM

    for i, r in enumerate(cfg["recipients"]):
        is_active = r.get("active", True)
        status_icon = "✅" if is_active else "⏸️"
        with st.expander(f"{status_icon} {'👑 ' if r['email']==OWNER else '👤 '}{r['name']}  —  {r['email']}", expanded=False):
            col1, col2 = st.columns(2)
            r["name"]  = col1.text_input("Name",  r["name"],  key=f"name_{i}")
            r["email"] = col2.text_input("Email", r["email"], key=f"email_{i}")

            r["cities"] = st.multiselect(
                "Cities", city_names, default=r.get("cities", []), key=f"cities_{i}"
            )

            r["active"] = st.toggle(
                "Active (receives emails)", value=r.get("active", True), key=f"active_{i}"
            )
            col3, col4 = st.columns(2)
            r["send_hour"] = col3.selectbox(
                "Send time (IST)", hours,
                index=hours.index(r.get("send_hour", 8)), key=f"hour_{i}",
                format_func=lambda h: f"{h}:00 AM" if h < 12 else "12:00 PM"
            )
            is_owner = r["email"] == OWNER
            r["daily_limit"] = not col4.checkbox(
                "No daily limit (owner)", value=not r.get("daily_limit", True),
                key=f"limit_{i}", disabled=is_owner
            ) if not is_owner else False

            if r["email"] != OWNER:
                if st.button(f"🗑️ Remove {r['name']}", key=f"del_{i}"):
                    cfg["recipients"].pop(i)
                    save_config(cfg)
                    st.rerun()

    st.divider()
    st.subheader("➕ Add recipient")
    with st.form("add_recipient"):
        c1, c2 = st.columns(2)
        new_name  = c1.text_input("Name")
        new_email = c2.text_input("Email")
        new_cities= st.multiselect("Cities", city_names)
        new_hour  = st.selectbox("Send time (IST)", hours, index=2,
                                  format_func=lambda h: f"{h}:00 AM")
        if st.form_submit_button("Add"):
            if new_name and new_email and new_cities:
                cfg["recipients"].append({
                    "name": new_name, "email": new_email,
                    "cities": new_cities, "daily_limit": True,
                    "send_hour": new_hour
                })
                save_config(cfg)
                st.rerun()
            else:
                st.error("Please fill in name, email and at least one city.")

    if st.button("💾 Save all changes"):
        save_config(cfg)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — CITIES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏙️ Cities":
    st.markdown("""<div style="background:linear-gradient(135deg,#1e293b,#0f2744);border-radius:16px;
    padding:24px 28px;margin-bottom:24px;border:1px solid #334155;">
    <h2 style="margin:0;color:#f1f5f9;">🏙️ Cities</h2>
    <p style="margin:6px 0 0 0;color:#64748b;">Manage city locations and AQI sampling points.</p>
    </div>""", unsafe_allow_html=True)

    for city, data in list(cfg["cities"].items()):
        with st.expander(f"📍 {city}", expanded=False):
            col1, col2 = st.columns(2)
            data["lat"] = col1.number_input("Latitude",  value=float(data["lat"]), format="%.4f", key=f"lat_{city}")
            data["lon"] = col2.number_input("Longitude", value=float(data["lon"]), format="%.4f", key=f"lon_{city}")
            st.caption("AQI sampling points (lat, lon pairs)")
            pts_str = st.text_area(
                "AQI points (one per line: lat,lon)",
                value="\n".join(f"{p[0]},{p[1]}" for p in data["aqi_points"]),
                key=f"pts_{city}"
            )
            data["aqi_points"] = [
                [float(x.strip()) for x in line.split(",")]
                for line in pts_str.strip().splitlines() if "," in line
            ]
            if city not in [r for rlist in [r["cities"] for r in cfg["recipients"]] for r in rlist]:
                if st.button(f"🗑️ Remove {city}", key=f"delcity_{city}"):
                    del cfg["cities"][city]
                    save_config(cfg)
                    st.rerun()

    st.divider()
    st.subheader("➕ Add city")
    with st.form("add_city"):
        c1, c2, c3 = st.columns(3)
        cname = c1.text_input("City name")
        clat  = c2.number_input("Latitude",  value=28.46, format="%.4f")
        clon  = c3.number_input("Longitude", value=77.03, format="%.4f")
        if st.form_submit_button("Add city"):
            if cname:
                cfg["cities"][cname] = {"lat": clat, "lon": clon, "aqi_points": [[clat, clon]]}
                save_config(cfg)
                st.rerun()

    if st.button("💾 Save all city changes"):
        save_config(cfg)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — RUN / TEST
# ══════════════════════════════════════════════════════════════════════════════
elif page == "▶️ Run / Test":
    st.markdown("""<div style="background:linear-gradient(135deg,#1e293b,#0f2744);border-radius:16px;
    padding:24px 28px;margin-bottom:24px;border:1px solid #334155;">
    <h2 style="margin:0;color:#f1f5f9;">▶️ Run / Test</h2>
    <p style="margin:6px 0 0 0;color:#64748b;">Send a test email to yourself or trigger a full run for all recipients.</p>
    </div>""", unsafe_allow_html=True)

    def inject_secrets():
        for key, val in st.secrets.items():
            os.environ[key] = str(val)

    def run_bot(test_only=False, bypass_hour=False):
        inject_secrets()
        if bypass_hour:
            os.environ["MANUAL_RUN"] = "1"
        elif "MANUAL_RUN" in os.environ:
            del os.environ["MANUAL_RUN"]

        sys.path.insert(0, BASE)
        import importlib, io, contextlib
        import weather_bot as wb
        importlib.reload(wb)

        log = io.StringIO()
        errors = []
        sent = []

        owner_email = st.secrets.get("JASMEET_EMAIL", "jasmeet27ghotra@gmail.com")
        recipients = [r for r in wb.RECIPIENTS if not test_only or r["email"] == owner_email]

        from datetime import datetime, timedelta
        today_date    = datetime.now().strftime("%d/%m/%Y")
        tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")

        for recipient in recipients:
            manual = os.environ.get("MANUAL_RUN") == "1"
            send_hour = recipient.get("send_hour", 8)
            if not manual and datetime.now().hour != send_hour:
                log.write(f"Skipping {recipient['email']} — not their hour.\n")
                continue
            if recipient.get("daily_limit") and wb.already_sent_today(recipient["email"]):
                log.write(f"Skipping {recipient['email']} — already sent today.\n")
                continue
            try:
                cities = recipient["cities"]
                city_data_list = [(city, *wb.city_cache[city]) for city in cities]
                city_label = " & ".join(cities)
                subject = f"🌤️ Weather Report ({city_label}) — {today_date} & {tomorrow_date}"
                plain = wb.build_plain(city_data_list, wb.thought, recipient.get("name",""))
                html  = wb.build_html(city_data_list, wb.thought, recipient.get("name",""))
                wb.send_email(recipient["email"], subject, plain, html)
                wb.log_email(recipient.get("name",""), recipient["email"], city_data_list, "sent")
                sent.append(recipient["email"])
                log.write(f"✅ Sent to {recipient['email']}\n")
            except Exception as e:
                errors.append(str(e))
                log.write(f"❌ Failed {recipient['email']}: {e}\n")

        return log.getvalue(), sent, errors

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🧪 Test email — only to me")
        if st.button("Send test email to Jasmeet", type="primary", use_container_width=True):
            with st.spinner("Sending..."):
                out, sent, errors = run_bot(test_only=True, bypass_hour=True)
            if sent:
                st.success("✅ Test email sent to Jasmeet!")
            if errors:
                st.error(f"❌ {errors[0]}")
            if sent or errors:
                commit_log()
            with st.expander("Output"):
                st.text(out)

    with col2:
        st.subheader("🚀 Full run — all recipients")
        bypass = st.checkbox("Bypass hour check (send regardless of scheduled time)")
        if st.button("Run weather bot now", use_container_width=True):
            with st.spinner("Running bot..."):
                out, sent, errors = run_bot(test_only=False, bypass_hour=bypass)
            if sent:
                st.success(f"✅ Sent to {len(sent)} recipient(s)!")
            if errors:
                st.error(f"❌ {errors[0]}")
            if sent or errors:
                commit_log()
            with st.expander("Output"):
                st.text(out)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — LOGS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Logs":
    st.markdown("""<div style="background:linear-gradient(135deg,#1e293b,#0f2744);border-radius:16px;
    padding:24px 28px;margin-bottom:24px;border:1px solid #334155;">
    <h2 style="margin:0;color:#f1f5f9;">📊 Email Logs</h2>
    <p style="margin:6px 0 0 0;color:#64748b;">Full history of every email sent or failed.</p>
    </div>""", unsafe_allow_html=True)

    import pandas as pd, io, requests as req

    # Always read latest log from GitHub (repo is public)
    RAW_LOG_URL = "https://raw.githubusercontent.com/jasmeet-dev/weather-bot/main/logs/email_log.csv"

    try:
        r = req.get(RAW_LOG_URL, timeout=10)
        if r.status_code == 200 and len(r.text.strip().splitlines()) > 1:
            df = pd.read_csv(io.StringIO(r.text))
        elif os.path.exists(LOG):
            df = pd.read_csv(LOG)
        else:
            st.info("No logs yet — logs appear after the first email run.")
            df = None
    except Exception:
        df = pd.read_csv(LOG) if os.path.exists(LOG) else None

    if df is not None:
        df = df.sort_values("timestamp", ascending=False)

        # Summary metrics
        today = datetime.now().strftime("%Y-%m-%d")
        sent_today = df[df["timestamp"].str.startswith(today) & (df["status"] == "sent")]

        col1, col2, col3 = st.columns(3)
        col1.metric("Total emails sent", len(df[df["status"] == "sent"]))
        col2.metric("Sent today", len(sent_today))
        col3.metric("Recipients active", df["email"].nunique())

        st.divider()

        # Filters
        fc1, fc2 = st.columns(2)
        name_filter  = fc1.multiselect("Filter by name",  df["name"].unique().tolist())
        city_filter  = fc2.multiselect("Filter by city",  df["cities"].unique().tolist())

        filtered = df.copy()
        if name_filter: filtered = filtered[filtered["name"].isin(name_filter)]
        if city_filter: filtered = filtered[filtered["cities"].isin(city_filter)]

        st.dataframe(
            filtered.style.map(
                lambda v: "color:green;font-weight:bold" if v == "sent"
                else "color:red" if isinstance(v, str) and "fail" in v else "",
                subset=["status"]
            ),
            use_container_width=True, height=500
        )

        st.download_button(
            "⬇️ Download CSV", df.to_csv(index=False),
            file_name="email_log.csv", mime="text/csv"
        )
