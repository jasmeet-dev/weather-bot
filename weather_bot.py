import os
import platform
import requests
import smtplib
import subprocess
from email.message import EmailMessage
from datetime import datetime, timedelta

EMAIL_ADDRESS = "jasmeet27ghotra@gmail.com"
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "shrm zocd cjut xbzi")

RECIPIENTS = [
    {"name": "Jasmeet",   "email": "jasmeet27ghotra@gmail.com",     "cities": ["Gurgaon", "Mohali"]},
    {"name": "Harsh",     "email": "harshsingh94@gmail.com",         "cities": ["Gurgaon"]},
    {"name": "Sukhwinder","email": "sukhwinder.singhepfo@gmail.com", "cities": ["Gurgaon", "Mohali"]},
    {"name": "Jasbir",    "email": "kjasbirkaur@gmail.com",          "cities": ["Mohali"]},
    {"name": "Gazaldeep", "email": "Gazaldeep.gk@gmail.com",         "cities": ["Mohali"]},
    {"name": "Abhijeet",  "email": "Abhijeetpnwr@gmail.com",         "cities": ["Mohali"]},
]

CITIES = {
    "Gurgaon": {"lat": 28.46, "lon": 77.03, "aqi_points": [(28.46, 77.03)]},
    "Mohali":  {"lat": 30.67, "lon": 76.76, "aqi_points": [
        (30.70, 76.72),  # Sector 64-70
        (30.67, 76.76),  # Sector 80-85
        (30.64, 76.82),  # Zirakpur
    ]},
}

PM25_BREAKPOINTS = [
    (0.0, 12.0, 0, 50), (12.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150), (55.5, 150.4, 151, 200),
    (150.5, 250.4, 201, 300), (250.5, 350.4, 301, 400),
    (350.5, 500.4, 401, 500),
]

def pm25_to_aqi(pm25):
    if pm25 is None: return None
    cp = round(pm25, 1)
    for clo, chi, ilo, ihi in PM25_BREAKPOINTS:
        if clo <= cp <= chi:
            return round((ihi - ilo) / (chi - clo) * (cp - clo) + ilo)
    return None

def aqi_label(val):
    if val is None: return ("N/A", "#888888")
    if val > 300:   return (f"{val} — HAZARDOUS", "#c0392b")
    if val > 150:   return (f"{val} — Unhealthy",  "#e67e22")
    if val > 100:   return (f"{val} — Moderate",   "#f0a500")
    if val > 50:    return (f"{val} — OK",          "#27ae60")
    return              (f"{val} — Good",           "#1a9e4a")

def fetch_pm25_avg(aqi_points, hour_index):
    readings = []
    for lat, lon in aqi_points:
        hourly = requests.get("https://air-quality-api.open-meteo.com/v1/air-quality", params={
            "latitude": lat, "longitude": lon,
            "hourly": "pm2_5", "timezone": "auto",
        }).json()["hourly"]["pm2_5"]
        val = hourly[hour_index] if isinstance(hour_index, int) else next((v for v in hourly[hour_index] if v is not None), None)
        if val is not None:
            readings.append(val)
    return sum(readings) / len(readings) if readings else None

def fetch_city_data(lat, lon, aqi_points):
    daily = requests.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": lat, "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,apparent_temperature_max,uv_index_max,sunrise,sunset",
        "timezone": "auto",
    }).json()["daily"]

    today = {
        "high": daily["temperature_2m_max"][0], "low": daily["temperature_2m_min"][0],
        "rain": daily["precipitation_probability_max"][0], "feels": daily["apparent_temperature_max"][0],
        "uv": daily["uv_index_max"][0],
        "sunrise": datetime.fromisoformat(daily["sunrise"][0]).strftime("%I:%M %p"),
        "sunset":  datetime.fromisoformat(daily["sunset"][0]).strftime("%I:%M %p"),
        "aqi": pm25_to_aqi(fetch_pm25_avg(aqi_points, datetime.now().hour)),
    }
    tomorrow = {
        "high": daily["temperature_2m_max"][1], "low": daily["temperature_2m_min"][1],
        "rain": daily["precipitation_probability_max"][1], "feels": daily["apparent_temperature_max"][1],
        "uv": daily["uv_index_max"][1],
        "sunrise": datetime.fromisoformat(daily["sunrise"][1]).strftime("%I:%M %p"),
        "sunset":  datetime.fromisoformat(daily["sunset"][1]).strftime("%I:%M %p"),
        "aqi": pm25_to_aqi(fetch_pm25_avg(aqi_points, slice(24+6, 24+19))),
    }
    return today, tomorrow

def advisories(today, tomorrow):
    tips = []
    aqi_val = today["aqi"]
    if aqi_val and aqi_val > 300:
        tips.append(("⚠️", "Air is HAZARDOUS — stay indoors, run a purifier."))
    elif aqi_val and aqi_val > 150:
        tips.append(("😷", "Air is unhealthy — limit outdoor time."))
    elif aqi_val and aqi_val > 100:
        tips.append(("😐", "Air is moderate — sensitive groups take care."))
    if today["rain"] >= 50 or tomorrow["rain"] >= 50:
        tips.append(("☂️", "Carry an umbrella!"))
    if today["high"] >= 38 or tomorrow["high"] >= 38:
        tips.append(("🥵", "It's going to be hot — stay hydrated and wear sunscreen if going out."))
    if today["uv"] >= 8 or tomorrow["uv"] >= 8:
        tips.append(("🌞", "UV is high — sunscreen mandatory if outdoors."))
    return tips

def weather_section_html(city_name, today, tomorrow):
    aqi_t_label,   aqi_t_color   = aqi_label(today["aqi"])
    aqi_tmr_label, aqi_tmr_color = aqi_label(tomorrow["aqi"])
    tips = advisories(today, tomorrow)
    tip_rows = "".join(
        f'<tr><td style="font-size:20px;padding:8px 12px;">{emoji}</td>'
        f'<td style="padding:8px 12px;color:#333;">{text}</td></tr>'
        for emoji, text in tips
    )
    suggestions_html = f"""
  <div class="suggestions">
    <h3>💡 Suggestions</h3>
    <table class="sug-table">{tip_rows}</table>
  </div>""" if tips else ""

    return f"""
  <h2>🌤️ {city_name} Weather</h2>
  <table>
    <thead><tr><th></th><th>☀️ TODAY</th><th>📅 TOMORROW</th></tr></thead>
    <tbody>
      <tr><td class="label-col">🌡️ High</td><td>{today['high']}°C</td><td>{tomorrow['high']}°C</td></tr>
      <tr><td class="label-col">🥵 Feels Like</td><td>{today['feels']}°C</td><td>{tomorrow['feels']}°C</td></tr>
      <tr><td class="label-col">❄️ Low</td><td>{today['low']}°C</td><td>{tomorrow['low']}°C</td></tr>
      <tr><td class="label-col">🌧️ Rain Chance</td><td>{today['rain']}%</td><td>{tomorrow['rain']}%</td></tr>
      <tr><td class="label-col">🌅 Sunrise</td><td>{today['sunrise']}</td><td>{tomorrow['sunrise']}</td></tr>
      <tr><td class="label-col">🌇 Sunset</td><td>{today['sunset']}</td><td>{tomorrow['sunset']}</td></tr>
      <tr>
        <td class="label-col">💨 AQI</td>
        <td style="color:{aqi_t_color};font-weight:bold;">{aqi_t_label}</td>
        <td style="color:{aqi_tmr_color};font-weight:bold;">{aqi_tmr_label}</td>
      </tr>
    </tbody>
  </table>{suggestions_html}"""

def build_html(city_data_list, thought, name=""):
    tables = "\n".join(weather_section_html(name, today, tmr) for name, today, tmr in city_data_list)
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; background: #f0f4f8; margin: 0; padding: 20px; }}
  .card {{ background: #ffffff; border-radius: 16px; max-width: 620px; margin: 0 auto;
           padding: 28px; box-shadow: 0 4px 16px rgba(0,0,0,0.10); }}
  .thought-box {{ background: #eef4ff; border-left: 5px solid #4a90d9; border-radius: 0 10px 10px 0;
                  padding: 14px 18px; margin-bottom: 28px; font-style: italic; color: #2c3e50; }}
  .thought-box .label {{ font-style: normal; font-weight: bold; font-size: 13px;
                          color: #4a90d9; text-transform: uppercase; margin-bottom: 6px; }}
  h2 {{ color: #2c3e50; margin: 24px 0 14px 0; font-size: 20px; }}
  h2:first-of-type {{ margin-top: 0; }}
  table {{ width: 100%; border-collapse: collapse; border-radius: 10px; overflow: hidden; margin-bottom: 8px; }}
  thead th {{ background: #2c3e50; color: #fff; padding: 12px 16px; font-size: 15px; }}
  thead th:first-child {{ text-align: left; }}
  thead th:not(:first-child) {{ text-align: center; }}
  tbody td {{ padding: 11px 16px; border-bottom: 1px solid #ecf0f1; color: #2c3e50; font-size: 14px; }}
  tbody td:not(:first-child) {{ text-align: center; }}
  tbody tr:last-child td {{ border-bottom: none; }}
  tbody tr:nth-child(even) {{ background: #f8fafc; }}
  .label-col {{ font-weight: 600; color: #555; }}
  .suggestions {{ margin-top: 16px; }}
  .suggestions h3 {{ margin: 0 0 10px 0; font-size: 16px; color: #2c3e50; }}
  .sug-table {{ width: 100%; border-collapse: collapse; }}
  .sug-table td {{ padding: 8px 12px; vertical-align: middle; }}
  .sug-table tr:nth-child(odd) {{ background: #fff8e1; }}
  .sug-table tr:nth-child(even) {{ background: #fdecea; }}
</style>
</head>
<body>
<div class="card">
  {f'<p style="font-size:16px;color:#2c3e50;margin:0 0 20px 0;">Dear {name},</p>' if name else ""}
  <div class="thought-box">
    <div class="label">💡 Thought of the Day</div>
    {thought}
  </div>
  {tables}
</div>
</body>
</html>"""

def build_plain(city_data_list, thought, name=""):
    lines = ([f"Dear {name},", ""] if name else []) + ["💡 THOUGHT OF THE DAY", f"   {thought}", ""]
    for city_name, today, tomorrow in city_data_list:
        aqi_t_label,   _ = aqi_label(today["aqi"])
        aqi_tmr_label, _ = aqi_label(tomorrow["aqi"])
        lines += [
            f"🌤️  {city_name.upper()} WEATHER",
            f"{'':16} {'TODAY':^18} {'TOMORROW':^18}",
            f"{'─'*52}",
            f"{'🌡️  High':<16} {str(today['high'])+'°C':^18} {str(tomorrow['high'])+'°C':^18}",
            f"{'🥵  Feels Like':<16} {str(today['feels'])+'°C':^18} {str(tomorrow['feels'])+'°C':^18}",
            f"{'❄️  Low':<16} {str(today['low'])+'°C':^18} {str(tomorrow['low'])+'°C':^18}",
            f"{'🌧️  Rain':<16} {str(today['rain'])+'%':^18} {str(tomorrow['rain'])+'%':^18}",
            f"{'🌅  Sunrise':<16} {today['sunrise']:^18} {tomorrow['sunrise']:^18}",
            f"{'🌇  Sunset':<16} {today['sunset']:^18} {tomorrow['sunset']:^18}",
            f"{'💨  AQI':<16} {aqi_t_label:^18} {aqi_tmr_label:^18}",
        ]
        tips = advisories(today, tomorrow)
        if tips:
            lines += ["", "💡 SUGGESTIONS"]
            for emoji, text in tips:
                lines.append(f"  {emoji}  {text}")
        lines.append("")
    return "\n".join(lines)

def send_email(to_email, subject, plain, html):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg.set_content(plain)
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

# --- Fetch data once per city ---
city_cache = {}
for city_name, coords in CITIES.items():
    city_cache[city_name] = fetch_city_data(coords["lat"], coords["lon"], coords["aqi_points"])

# --- Thought of the Day ---
try:
    q = requests.get("https://zenquotes.io/api/today", timeout=5).json()[0]
    thought = f'"{q["q"]}" — {q["a"]}'
except Exception:
    thought = "Make today count."

today_date    = datetime.now().strftime("%d/%m/%Y")
tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")

# --- Mac notification (Gurgaon, local only) ---
if platform.system() == "Darwin":
    g_today, g_tomorrow = city_cache["Gurgaon"]
    notif_plain = build_plain([("Gurgaon", g_today, g_tomorrow)], thought, "Jasmeet")
    safe = notif_plain.replace('"', '\\"')
    subprocess.run(["osascript", "-e",
        f'display dialog "{safe}" with title "🌤️ Weather Bot" buttons {{"OK"}} default button "OK"'])

# --- Send personalized emails ---
for recipient in RECIPIENTS:
    cities         = recipient["cities"]
    city_data_list = [(city, *city_cache[city]) for city in cities]
    city_label     = " & ".join(cities)
    subject        = f"🌤️ Weather Report ({city_label}) — {today_date} & {tomorrow_date}"
    plain          = build_plain(city_data_list, thought, recipient.get("name", ""))
    html           = build_html(city_data_list, thought, recipient.get("name", ""))
    print(f"Sending to {recipient['email']} ({city_label})...")
    print(plain)
    send_email(recipient["email"], subject, plain, html)
