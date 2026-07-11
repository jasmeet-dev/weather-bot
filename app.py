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

# ── password gate ─────────────────────────────────────────────────────────────
def check_password():
    correct = st.secrets.get("APP_PASSWORD", "weatherbot123")
    if st.session_state.get("authenticated"):
        return True
    with st.form("login"):
        st.title("🌤️ Weather Bot")
        pw = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
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

def save_config(cfg):
    import base64, requests as req
    content = json.dumps(cfg, indent=2)

    token = st.secrets.get("GITHUB_TOKEN", "")
    if token:
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        api_url = "https://api.github.com/repos/jasmeet-dev/weather-bot/contents/config.json"
        r = req.get(api_url, headers=headers)
        sha = r.json().get("sha", "")
        payload = {
            "message": "GUI: update config.json",
            "content": base64.b64encode(content.encode()).decode(),
            "sha": sha
        }
        resp = req.put(api_url, json=payload, headers=headers)
        if resp.status_code in (200, 201):
            st.success("✅ Config saved and committed to GitHub!")
        else:
            st.error(f"❌ GitHub save failed: {resp.json().get('message')}")
    else:
        with open(CONFIG, "w") as f:
            f.write(content)
        st.success("Config saved locally!")

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
st.sidebar.image("https://img.icons8.com/fluency/96/partly-cloudy-day.png", width=60)
st.sidebar.title("🌤️ Weather Bot")
st.sidebar.caption("Control panel")
page = st.sidebar.radio("", ["📋 Recipients", "🏙️ Cities", "▶️ Run / Test", "📊 Logs"])

cfg = load_config()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — RECIPIENTS
# ══════════════════════════════════════════════════════════════════════════════
if page == "📋 Recipients":
    st.title("📋 Recipients")
    st.caption("Add, edit or remove people who receive the daily weather email.")

    city_names = list(cfg["cities"].keys())
    hours      = list(range(6, 13))   # 6 AM – 12 PM

    for i, r in enumerate(cfg["recipients"]):
        with st.expander(f"{'👑 ' if r['email']==OWNER else '👤 '}{r['name']}  —  {r['email']}", expanded=False):
            col1, col2 = st.columns(2)
            r["name"]  = col1.text_input("Name",  r["name"],  key=f"name_{i}")
            r["email"] = col2.text_input("Email", r["email"], key=f"email_{i}")

            r["cities"] = st.multiselect(
                "Cities", city_names, default=r.get("cities", []), key=f"cities_{i}"
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
    st.title("🏙️ Cities")
    st.caption("Manage cities and their coordinates.")

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
    st.title("▶️ Run / Test")
    st.info("**Test email** sends only to you (Jasmeet). **Full run** sends to everyone based on their scheduled time and daily limit.")

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
            with st.expander("Output"):
                st.text(out)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — LOGS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Logs":
    st.title("📊 Email Logs")

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
