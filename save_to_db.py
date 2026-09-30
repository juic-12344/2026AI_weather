import sqlite3
import urllib3
import requests

# 忽略 SSL 憑證警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 你的真實 API 金鑰
API_KEY = "CWA-B7027CBB-4D9D-415E-A5A3-737F76555BAA"
url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={API_KEY}"

response = requests.get(url, verify=False)
data = response.json()

# 連線到資料庫
conn = sqlite3.connect("weather_data.db")
cursor = conn.cursor()

# 先刪除舊表格，確保欄位結構完全正確
cursor.execute("DROP TABLE IF EXISTS TemperatureForecasts")

# 重新建立包含所有欄位的表格
cursor.execute("""
    CREATE TABLE TemperatureForecasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        regionName TEXT,
        startTime TEXT,
        endTime TEXT,
        wx TEXT,
        minTemp TEXT,
        maxTemp TEXT,
        pop TEXT
    )
""")

# 解析 JSON 資料並寫入多個時間段
locations = data["records"]["location"]
for loc in locations:
  region_name = loc["locationName"]
  weather_elements = loc["weatherElement"]

  wx_times = weather_elements[0]["time"]
  mint_times = weather_elements[2]["time"]
  maxt_times = weather_elements[4]["time"]
  pop_times = weather_elements[1]["time"]

  for i in range(len(wx_times)):
    start_time = wx_times[i]["startTime"]
    end_time = wx_times[i]["endTime"]
    wx = wx_times[i]["parameter"]["parameterName"]
    min_temp = mint_times[i]["parameter"]["parameterName"]
    max_temp = maxt_times[i]["parameter"]["parameterName"]
    pop = pop_times[i]["parameter"]["parameterName"]

    cursor.execute(
        """
        INSERT INTO TemperatureForecasts (regionName, startTime, endTime, wx, minTemp, maxTemp, pop)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (region_name, start_time, end_time, wx, min_temp, max_temp, pop),
    )

conn.commit()
conn.close()
print("多時段氣象資料已成功寫入資料庫！")