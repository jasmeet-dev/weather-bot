import os
import platform
import requests
import smtplib
import subprocess
from email.message import EmailMessage
from datetime import datetime, timedelta

EMAIL_ADDRESS = "jasmeet27ghotra@gmail.com"
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "shrm zocd cjut xbzi")
EMAIL_TO = [
    "jasmeet27ghotra@gmail.com",
    "harshsingh94@gmail.com",
    "sukhvindersinghepfo@gmail.com",
]

LATITUDE = 28.61
LONGITUDE = 77.21
GURGAON_LAT = 28.46
GURGAON_LON = 77.03

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

def advisories(today_high, today_rain, today_uv, aqi_val, tmr_high, tmr_rain, tmr_uv):
    tips = []
    if aqi_val and aqi_val > 300:
        tips.append(("⚠️", "Air is HAZARDOUS — stay indoors, run a purifier."))
    elif aqi_val and aqi_val > 150:
        tips.append(("😷", "Air is unhealthy — limit outdoor time."))
    elif aqi_val and aqi_val > 100:
        tips.append(("😐", "Air is moderate — sensitive groups take care."))
    if today_rain >= 50 or tmr_rain >= 50:
        tips.append(("☂️", "Carry an umbrella!"))
    if today_high >= 38 or tmr_high >= 38:
        tips.append(("🥵", "It's going to be hot — stay hydrated and wear sunscreen if going out."))
    if today_uv >= 8 or tmr_uv >= 8:
        tips.append(("🌞", "UV is high — sunscreen mandatory if outdoors."))
    return tips

def build_html(today, tomorrow, aqi_today, aqi_tomorrow, thought, tips):
    aqi_t_label,  aqi_t_color  = aqi_label(aqi_today)
    aqi_tmr_label, aqi_tmr_color = aqi_label(aqi_tomorrow)

    tip_rows = "".join(
        f'<tr><td style="font-size:20px;padding:8px 12px;">{emoji}</td>'
        f'<td style="padding:8px 12px;color:#333;">{text}</td></tr>'
        for emoji, text in tips
    )

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
  h2 {{ color: #2c3e50; margin: 0 0 14px 0; font-size: 20px; }}
  table {{ width: 100%; border-collapse: collapse; border-radius: 10px; overflow: hidden; }}
  thead th {{ background: #2c3e50; color: #fff; padding: 12px 16px; font-size: 15px; }}
  thead th:first-child {{ text-align: left; }}
  thead th:not(:first-child) {{ text-align: center; }}
  tbody td {{ padding: 11px 16px; border-bottom: 1px solid #ecf0f1; color: #2c3e50; font-size: 14px; }}
  tbody td:not(:first-child) {{ text-align: center; }}
  tbody tr:last-child td {{ border-bottom: none; }}
  tbody tr:nth-child(even) {{ background: #f8fafc; }}
  .label-col {{ font-weight: 600; color: #555; }}
  .suggestions {{ margin-top: 24px; }}
  .suggestions h2 {{ margin-bottom: 10px; }}
  .sug-table {{ width: 100%; border-collapse: collapse; }}
  .sug-table td {{ padding: 8px 12px; vertical-align: middle; }}
  .sug-table tr {{ border-radius: 8px; }}
  .sug-table tr:nth-child(odd) {{ background: #fff8e1; }}
  .sug-table tr:nth-child(even) {{ background: #fdecea; }}
</style>
</head>
<body>
<div class="card">

  <div class="thought-box">
    <div class="label">💡 Thought of the Day</div>
    {thought}
  </div>

  <h2>🌤️ Weather Report</h2>
  <table>
    <thead>
      <tr>
        <th></th>
        <th>☀️ TODAY</th>
        <th>📅 TOMORROW</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td class="label-col">🌡️ High</td>
        <td>{today['high']}°C</td>
        <td>{tomorrow['high']}°C</td>
      </tr>
      <tr>
        <td class="label-col">🥵 Feels Like</td>
        <td>{today['feels']}°C</td>
        <td>{tomorrow['feels']}°C</td>
      </tr>
      <tr>
        <td class="label-col">❄️ Low</td>
        <td>{today['low']}°C</td>
        <td>{tomorrow['low']}°C</td>
      </tr>
      <tr>
        <td class="label-col">🌧️ Rain Chance</td>
        <td>{today['rain']}%</td>
        <td>{tomorrow['rain']}%</td>
      </tr>
      <tr>
        <td class="label-col">🌅 Sunrise</td>
        <td>{today['sunrise']}</td>
        <td>{tomorrow['sunrise']}</td>
      </tr>
      <tr>
        <td class="label-col">🌇 Sunset</td>
        <td>{today['sunset']}</td>
        <td>{tomorrow['sunset']}</td>
      </tr>
      <tr>
        <td class="label-col">💨 AQI (Gurgaon)</td>
        <td style="color:{aqi_t_color};font-weight:bold;">{aqi_t_label}</td>
        <td style="color:{aqi_tmr_color};font-weight:bold;">{aqi_tmr_label}</td>
      </tr>
    </tbody>
  </table>

  {"" if not tips else f'''
  <div class="suggestions">
    <h2>💡 Suggestions</h2>
    <table class="sug-table">
      {tip_rows}
    </table>
  </div>'''}

</div>
</body>
</html>"""

def build_plain(today, tomorrow, aqi_today, aqi_tomorrow, thought, tips):
    aqi_t_label,  _ = aqi_label(aqi_today)
    aqi_tmr_label, _ = aqi_label(aqi_tomorrow)
    lines = [
        "💡 THOUGHT OF THE DAY",
        f"   {thought}",
        "",
        "🌤️  WEATHER REPORT",
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
    if tips:
        lines += ["", "💡 SUGGESTIONS"]
        for emoji, text in tips:
            lines.append(f"  {emoji}  {text}")
    return "\n".join(lines)

def send_email(subject, plain, html):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = ", ".join(EMAIL_TO)
    msg.set_content(plain)
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

# --- Weather API ---
daily = requests.get("https://api.open-meteo.com/v1/forecast", params={
    "latitude": LATITUDE, "longitude": LONGITUDE,
    "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,apparent_temperature_max,uv_index_max,sunrise,sunset",
    "timezone": "auto",
}).json()["daily"]

today    = {"high": daily["temperature_2m_max"][0], "low": daily["temperature_2m_min"][0],
            "rain": daily["precipitation_probability_max"][0], "feels": daily["apparent_temperature_max"][0],
            "uv": daily["uv_index_max"][0],
            "sunrise": datetime.fromisoformat(daily["sunrise"][0]).strftime("%I:%M %p"),
            "sunset":  datetime.fromisoformat(daily["sunset"][0]).strftime("%I:%M %p")}
tomorrow = {"high": daily["temperature_2m_max"][1], "low": daily["temperature_2m_min"][1],
            "rain": daily["precipitation_probability_max"][1], "feels": daily["apparent_temperature_max"][1],
            "uv": daily["uv_index_max"][1],
            "sunrise": datetime.fromisoformat(daily["sunrise"][1]).strftime("%I:%M %p"),
            "sunset":  datetime.fromisoformat(daily["sunset"][1]).strftime("%I:%M %p")}

# --- AQI (open-meteo PM2.5 → US AQI) ---
pm25_hourly = requests.get("https://air-quality-api.open-meteo.com/v1/air-quality", params={
    "latitude": GURGAON_LAT, "longitude": GURGAON_LON,
    "hourly": "pm2_5", "timezone": "auto",
}).json()["hourly"]["pm2_5"]
aqi_today    = pm25_to_aqi(pm25_hourly[datetime.now().hour])
aqi_tomorrow = pm25_to_aqi(next((v for v in pm25_hourly[24+6:24+19] if v is not None), None))

# --- Thought of the Day ---
try:
    q = requests.get("https://zenquotes.io/api/today", timeout=5).json()[0]
    thought = f'"{q["q"]}" — {q["a"]}'
except Exception:
    thought = "Make today count."

tips = advisories(today["high"], today["rain"], today["uv"],
                  aqi_today, tomorrow["high"], tomorrow["rain"], tomorrow["uv"])

plain = build_plain(today, tomorrow, aqi_today, aqi_tomorrow, thought, tips)
html  = build_html(today, tomorrow, aqi_today, aqi_tomorrow, thought, tips)

# --- Mac notification (local only) ---
if platform.system() == "Darwin":
    safe = plain.replace('"', '\\"')
    subprocess.run(["osascript", "-e",
        f'display dialog "{safe}" with title "🌤️ Weather Bot" buttons {{"OK"}} default button "OK"'])

today_date    = datetime.now().strftime("%d/%m/%Y")
tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
subject = f"🌤️ Weather Report — {today_date} & {tomorrow_date}"

print(plain)
send_email(subject, plain, html)
