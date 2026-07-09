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
    {"name": "Harsh",     "email": "harshsingh94@gmail.com",         "cities": ["Gurgaon", "Mohali"]},
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
    resp = requests.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": lat, "longitude": lon,
        "daily":  "temperature_2m_max,temperature_2m_min,precipitation_probability_max,apparent_temperature_max,uv_index_max,sunrise,sunset",
        "hourly": "temperature_2m,precipitation_probability,weathercode,windspeed_10m,relativehumidity_2m",
        "timezone": "auto",
    }).json()
    daily = resp["daily"]
    h     = resp["hourly"]
    now   = datetime.now().hour
    today = {
        "high": daily["temperature_2m_max"][0], "low": daily["temperature_2m_min"][0],
        "rain": daily["precipitation_probability_max"][0], "feels": daily["apparent_temperature_max"][0],
        "uv": daily["uv_index_max"][0],
        "sunrise": datetime.fromisoformat(daily["sunrise"][0]).strftime("%I:%M %p"),
        "sunset":  datetime.fromisoformat(daily["sunset"][0]).strftime("%I:%M %p"),
        "aqi": pm25_to_aqi(fetch_pm25_avg(aqi_points, now)),
        "temp_now":  h["temperature_2m"][now],
        "wind_now":  round(h["windspeed_10m"][now]),
        "humid_now": h["relativehumidity_2m"][now],
        "code_now":  h["weathercode"][now],
        "hourly_temps": h["temperature_2m"],
        "hourly_codes": h["weathercode"],
    }
    tomorrow = {
        "high": daily["temperature_2m_max"][1], "low": daily["temperature_2m_min"][1],
        "rain": daily["precipitation_probability_max"][1], "feels": daily["apparent_temperature_max"][1],
        "uv": daily["uv_index_max"][1],
        "sunrise": datetime.fromisoformat(daily["sunrise"][1]).strftime("%I:%M %p"),
        "sunset":  datetime.fromisoformat(daily["sunset"][1]).strftime("%I:%M %p"),
        "aqi": pm25_to_aqi(fetch_pm25_avg(aqi_points, slice(24+6, 24+19))),
        "code_now": h["weathercode"][24],
    }
    return today, tomorrow

WEATHER_ICON = {
    0:"☀️",1:"🌤️",2:"⛅",3:"☁️",45:"🌫️",48:"🌫️",
    51:"🌦️",53:"🌦️",55:"🌦️",61:"🌧️",63:"🌧️",65:"🌧️",
    71:"🌨️",73:"🌨️",75:"🌨️",80:"🌧️",81:"🌧️",82:"🌧️",
    95:"⛈️",96:"⛈️",99:"⛈️",
}
WEATHER_DESC = {
    0:"Clear Sky",1:"Mainly Clear",2:"Partly Cloudy",3:"Overcast",
    45:"Foggy",48:"Foggy",51:"Light Drizzle",53:"Drizzle",55:"Heavy Drizzle",
    61:"Light Rain",63:"Rain",65:"Heavy Rain",71:"Light Snow",73:"Snow",75:"Heavy Snow",
    80:"Rain Showers",81:"Rain Showers",82:"Heavy Showers",
    95:"Thunderstorm",96:"Thunderstorm",99:"Severe Thunderstorm",
}

WEATHER_THEMES = {
    "sunny":   {"name":"Sunny",        "dark":False,"body":"#fffbf0","grad":"linear-gradient(160deg,#ffffff 0%,#fef9e7 50%,#fef3c7 100%)","c1":"rgba(251,191,36,0.15)", "c2":"rgba(251,146,60,0.1)", "bdr":"rgba(251,191,36,0.4)","acc":"#d97706","acc2":"#ea580c","mut":"#78350f","sub":"#92400e","txt":"#451a03","tmp":"#b45309"},
    "pcloudy": {"name":"Partly Cloudy","dark":False,"body":"#f0f9ff","grad":"linear-gradient(160deg,#ffffff 0%,#e0f2fe 55%,#bae6fd 100%)","c1":"rgba(14,165,233,0.12)", "c2":"rgba(14,165,233,0.08)","bdr":"rgba(14,165,233,0.3)","acc":"#0284c7","acc2":"#0ea5e9","mut":"#0c4a6e","sub":"#075985","txt":"#0c4a6e","tmp":"#0369a1"},
    "overcast":{"name":"Overcast",     "dark":False,"body":"#f8fafc","grad":"linear-gradient(160deg,#ffffff 0%,#f1f5f9 55%,#e2e8f0 100%)","c1":"rgba(100,116,139,0.12)","c2":"rgba(100,116,139,0.08)","bdr":"rgba(100,116,139,0.3)","acc":"#475569","acc2":"#64748b","mut":"#334155","sub":"#64748b","txt":"#1e293b","tmp":"#334155"},
    "foggy":   {"name":"Foggy",        "dark":False,"body":"#f5f5f0","grad":"linear-gradient(160deg,#fafaf8 0%,#f0f0e8 55%,#e8e8dc 100%)","c1":"rgba(120,113,108,0.12)","c2":"rgba(120,113,108,0.08)","bdr":"rgba(120,113,108,0.25)","acc":"#57534e","acc2":"#78716c","mut":"#44403c","sub":"#78716c","txt":"#1c1917","tmp":"#44403c"},
    "drizzle": {"name":"Drizzle",      "dark":False,"body":"#eff6ff","grad":"linear-gradient(160deg,#ffffff 0%,#dbeafe 55%,#bfdbfe 100%)","c1":"rgba(59,130,246,0.12)", "c2":"rgba(59,130,246,0.08)","bdr":"rgba(59,130,246,0.3)","acc":"#2563eb","acc2":"#3b82f6","mut":"#1e3a8a","sub":"#1d4ed8","txt":"#1e3a8a","tmp":"#1d4ed8"},
    "rainy":   {"name":"Rainy",        "dark":True, "body":"#0a0f1e","grad":"linear-gradient(160deg,#0c1445 0%,#1a237e 50%,#0d1b4b 100%)","c1":"rgba(66,165,245,0.15)","c2":"rgba(66,165,245,0.1)","bdr":"rgba(66,165,245,0.3)","acc":"#42a5f5","acc2":"#29b6f6","mut":"#90caf9","sub":"#1565c0","txt":"white","tmp":"#64b5f6"},
    "snowy":   {"name":"Snowy",        "dark":False,"body":"#f0f8ff","grad":"linear-gradient(160deg,#ffffff 0%,#e8f4fd 50%,#d6eaf8 100%)","c1":"rgba(41,182,246,0.12)", "c2":"rgba(41,182,246,0.08)","bdr":"rgba(41,182,246,0.3)","acc":"#0288d1","acc2":"#29b6f6","mut":"#01579b","sub":"#0277bd","txt":"#01579b","tmp":"#0288d1"},
    "thunder": {"name":"Thunderstorm", "dark":True, "body":"#0d0d1a","grad":"linear-gradient(160deg,#0d0d1a 0%,#1a0a2e 55%,#0a1a28 100%)","c1":"rgba(167,139,250,0.15)","c2":"rgba(167,139,250,0.08)","bdr":"rgba(167,139,250,0.4)","acc":"#a78bfa","acc2":"#c4b5fd","mut":"#ddd6fe","sub":"#7c3aed","txt":"white","tmp":"#c4b5fd"},
}

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

def pick_theme(city_data_list):
    code = city_data_list[0][1].get("code_now", 0)
    if code == 0:                             return WEATHER_THEMES["sunny"]
    if code in (1, 2):                        return WEATHER_THEMES["pcloudy"]
    if code == 3:                             return WEATHER_THEMES["overcast"]
    if code in (45, 48):                      return WEATHER_THEMES["foggy"]
    if code in range(51, 58):                 return WEATHER_THEMES["drizzle"]
    if code in (*range(61,66),*range(80,83)): return WEATHER_THEMES["rainy"]
    if code in (*range(71,78), 85, 86):       return WEATHER_THEMES["snowy"]
    if code in (95, 96, 99):                  return WEATHER_THEMES["thunder"]
    return WEATHER_THEMES["pcloudy"]

def hourly_strip(today, t):
    slots = [6, 9, 12, 15, 18, 21]
    cells = ""
    for h in slots:
        icon  = WEATHER_ICON.get(today["hourly_codes"][h], "🌡️")
        temp  = round(today["hourly_temps"][h])
        label = datetime(2000,1,1,h).strftime("%-I %p")
        cells += (f'<td style="text-align:center;padding:0 6px;">'
                  f'<div style="font-size:11px;color:{t["sub"]};margin-bottom:6px;">{label}</div>'
                  f'<div style="font-size:22px;line-height:1;">{icon}</div>'
                  f'<div style="font-size:13px;font-weight:700;color:{t["acc"]};margin-top:6px;">{temp}°</div>'
                  f'</td>')
    return (f'<table width="100%" cellpadding="0" cellspacing="0" '
            f'style="border-collapse:collapse;margin-top:12px;"><tr>{cells}</tr></table>')

def city_card(city_name, today, tomorrow, t, thought=None):
    icon     = WEATHER_ICON.get(today["code_now"], "🌡️")
    desc     = WEATHER_DESC.get(today["code_now"], "")
    tmr_icon = WEATHER_ICON.get(tomorrow.get("code_now", 0), "🌡️")
    aqi_lbl,  aqi_col  = aqi_label(today["aqi"])
    aqi_lbl2, aqi_col2 = aqi_label(tomorrow["aqi"])
    tips     = advisories(today, tomorrow)
    tip_rows = "".join(
        f'<tr><td style="padding:5px 0;font-size:13px;color:{t["mut"]};">{e} {tx}</td></tr>'
        for e, tx in tips
    )
    thought_box = (
        f'<div style="background:{t["c1"]};border-left:3px solid {t["acc"]};'
        f'border-radius:0 10px 10px 0;padding:12px 16px;margin-bottom:20px;'
        f'font-style:italic;color:{t["mut"]};font-size:13px;">'
        f'<div style="font-style:normal;font-size:10px;font-weight:700;color:{t["acc"]};'
        f'letter-spacing:1px;text-transform:uppercase;margin-bottom:5px;">Thought of the Day</div>'
        f'{thought}</div>'
    ) if thought else ""
    shadow = "0 4px 24px rgba(0,0,0,0.35)" if t["dark"] else "0 8px 32px rgba(0,0,0,0.10)"
    return f"""
<div style="background:{t['grad']};border-radius:20px;padding:28px 24px;margin-bottom:20px;
            box-shadow:{shadow};font-family:Arial,sans-serif;">
  {thought_box}
  <div style="text-align:center;margin-bottom:16px;">
    <div style="font-size:22px;font-weight:800;color:{t['txt']};">{city_name}</div>
    <div style="font-size:13px;color:{t['sub']};margin-top:2px;">{desc}</div>
  </div>
  <div style="text-align:center;margin-bottom:4px;">
    <div style="font-size:76px;line-height:1.1;">{icon}</div>
    <div style="font-size:54px;font-weight:300;color:{t['tmp']};margin-top:8px;">{today['temp_now']}°<span style="font-size:22px;color:{t['sub']};">C</span></div>
    <div style="font-size:13px;color:{t['sub']};margin-top:4px;">H:{today['high']}° &nbsp; Feels {today['feels']}° &nbsp; L:{today['low']}°</div>
  </div>
  <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:separate;border-spacing:8px;margin:20px 0;">
    <tr>
      <td style="background:{t['c1']};border-radius:14px;padding:14px 8px;text-align:center;width:33%;">
        <div style="font-size:20px;">🌧️</div>
        <div style="font-size:16px;font-weight:700;color:{t['acc']};margin:4px 0;">{today['rain']}%</div>
        <div style="font-size:11px;color:{t['sub']};">Precipitation</div>
      </td>
      <td style="background:{t['c1']};border-radius:14px;padding:14px 8px;text-align:center;width:33%;">
        <div style="font-size:20px;">💧</div>
        <div style="font-size:16px;font-weight:700;color:{t['acc']};margin:4px 0;">{today['humid_now']}%</div>
        <div style="font-size:11px;color:{t['sub']};">Humidity</div>
      </td>
      <td style="background:{t['c1']};border-radius:14px;padding:14px 8px;text-align:center;width:33%;">
        <div style="font-size:20px;">💨</div>
        <div style="font-size:16px;font-weight:700;color:{t['acc']};margin:4px 0;">{today['wind_now']} km/h</div>
        <div style="font-size:11px;color:{t['sub']};">Wind Speed</div>
      </td>
    </tr>
  </table>
  <div style="background:{t['c1']};border-radius:16px;padding:16px;">
    <div style="font-size:11px;color:{t['sub']};font-weight:700;letter-spacing:1px;text-transform:uppercase;">Today — Hourly</div>
    {hourly_strip(today, t)}
  </div>
  <div style="background:{t['c1']};border-radius:16px;padding:14px 18px;margin-top:10px;">
    <div style="font-size:11px;color:{t['sub']};font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;">Tomorrow</div>
    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
      <tr>
        <td style="font-size:13px;color:{t['mut']};vertical-align:middle;"><span style="font-size:20px;">{tmr_icon}</span>&nbsp; H:{tomorrow['high']}° L:{tomorrow['low']}°</td>
        <td style="text-align:right;font-size:13px;color:{t['mut']};">🌧️ Rain {tomorrow['rain']}%</td>
      </tr>
    </table>
  </div>
  <div style="background:{t['c1']};border-radius:16px;padding:14px 18px;margin-top:10px;">
    <div style="font-size:11px;color:{t['sub']};font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;">Air Quality (AQI)</div>
    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
      <tr><td style="font-size:13px;color:{t['mut']};">Today</td><td style="text-align:right;font-weight:700;color:{aqi_col};">{aqi_lbl}</td></tr>
      <tr><td style="font-size:13px;color:{t['mut']};padding-top:4px;">Tomorrow</td><td style="text-align:right;font-weight:700;color:{aqi_col2};padding-top:4px;">{aqi_lbl2}</td></tr>
    </table>
  </div>
  <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:separate;border-spacing:8px;margin-top:10px;">
    <tr>
      <td style="background:{t['c2']};border-radius:12px;padding:10px 8px;text-align:center;">
        <div style="font-size:16px;">🌅</div>
        <div style="font-size:13px;font-weight:700;color:{t['acc2']};margin:2px 0;">{today['sunrise']}</div>
        <div style="font-size:10px;color:{t['sub']};">Sunrise · Today</div>
      </td>
      <td style="background:{t['c2']};border-radius:12px;padding:10px 8px;text-align:center;">
        <div style="font-size:16px;">🌇</div>
        <div style="font-size:13px;font-weight:700;color:{t['acc2']};margin:2px 0;">{today['sunset']}</div>
        <div style="font-size:10px;color:{t['sub']};">Sunset · Today</div>
      </td>
      <td style="background:{t['c2']};border-radius:12px;padding:10px 8px;text-align:center;">
        <div style="font-size:16px;">🌅</div>
        <div style="font-size:13px;font-weight:700;color:{t['acc2']};margin:2px 0;">{tomorrow['sunrise']}</div>
        <div style="font-size:10px;color:{t['sub']};">Sunrise · Tomorrow</div>
      </td>
      <td style="background:{t['c2']};border-radius:12px;padding:10px 8px;text-align:center;">
        <div style="font-size:16px;">🌇</div>
        <div style="font-size:13px;font-weight:700;color:{t['acc2']};margin:2px 0;">{tomorrow['sunset']}</div>
        <div style="font-size:10px;color:{t['sub']};">Sunset · Tomorrow</div>
      </td>
    </tr>
  </table>
  {f'''<div style="background:{t["c2"]};border:1px solid {t["bdr"]};border-radius:14px;padding:14px 16px;margin-top:10px;">
    <div style="font-size:11px;color:{t["acc"]};font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;">Suggestions</div>
    <table cellpadding="0" cellspacing="0" style="border-collapse:collapse;width:100%;">{tip_rows}</table>
  </div>''' if tips else ""}
</div>"""

def build_html(city_data_list, thought, recipient_name="", theme=None):
    t = theme or WEATHER_THEMES["pcloudy"]
    name = recipient_name
    sections = ""
    for i, (city_name, today, tmr) in enumerate(city_data_list):
        sections += city_card(city_name, today, tmr, t, thought if i == 0 else None)
    txt_color = t["txt"]
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:16px;background:{t['body']};font-family:Arial,sans-serif;">
<div style="max-width:560px;margin:0 auto;">
  {f'<p style="color:{txt_color};font-size:15px;margin:0 0 16px 10px;">Dear {name},</p>' if name else ""}
  {sections}
</div></body></html>"""

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
    name           = recipient.get("name", "")
    theme          = pick_theme(city_data_list)
    plain          = build_plain(city_data_list, thought, name)
    html           = build_html(city_data_list, thought, name, theme)
    print(f"Sending to {recipient['email']} ({city_label}) [{theme['name']}]...")
    print(plain)
    send_email(recipient["email"], subject, plain, html)
