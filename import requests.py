import sqlite3
import requests
import urllib3

# 關閉憑證警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 1. 設定氣象署的 API 網址與 API Key
url = 'https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001'
params = {
    'Authorization': 'CWA-B7027CBB-4D9D-415E-A5A3-737F76555BAA'
}

# 2. 發送請求取得資料
response = requests.get(url, params=params, verify=False)
data = response.json()

# ==========================================
# 3. 建立 SQLite 資料庫並儲存資料
# ==========================================

# 連線到一個叫做 weather_data.db 的資料庫（如果沒有這個檔案，Python會自動幫你建立）
conn = sqlite3.connect('weather_data.db')
cursor = conn.cursor()

# 建立一個名為 TemperatureForecasts 的資料表（如果已經存在就先刪掉重建，方便我們測試）
cursor.execute('''
    CREATE TABLE IF NOT EXISTS TemperatureForecasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        regionName TEXT,
        minTemp TEXT,
        maxTemp TEXT,
        startTime TEXT,
        endTime TEXT
    )
''')

# 先清空舊資料（避免重複一直加進去）
cursor.execute('DELETE FROM TemperatureForecasts')

# 解析 JSON 並把資料插入資料庫
locations = data['records']['location']

for loc in locations:
    loc_name = loc['locationName']
    min_temp = ""
    max_temp = ""
    start_time = ""
    end_time = ""
    
    for element in loc['weatherElement']:
        if element['elementName'] == 'MinT':
            min_temp = element['time'][0]['parameter']['parameterName']
            start_time = element['time'][0]['startTime']
            end_time = element['time'][0]['endTime']
        elif element['elementName'] == 'MaxT':
            max_temp = element['time'][0]['parameter']['parameterName']

    # 將抓到的資料寫入 SQL 表格
    cursor.execute('''
        INSERT INTO TemperatureForecasts (regionName, minTemp, maxTemp, startTime, endTime)
        VALUES (?, ?, ?, ?, ?)
    ''', (loc_name, min_temp, max_temp, start_time, end_time))

# 提交變更並關閉資料庫連線
conn.commit()
conn.close()

print("🎉 太棒了！氣溫資料已經成功存入 SQLite 資料庫（weather_data.db）中！")