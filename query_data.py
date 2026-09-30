import sqlite3

# 1. 連線到我們剛剛建立的資料庫檔案
conn = sqlite3.connect('weather_data.db')
cursor = conn.cursor()

# 2. 使用 SQL 語法：從 TemperatureForecasts 表格中查詢所有資料
cursor.execute('SELECT regionName, minTemp, maxTemp, startTime FROM TemperatureForecasts')

# 3. 把查詢到的所有資料通通抓回來
rows = cursor.fetchall()

print("========== 從資料庫查詢到的氣溫資料 ==========")

# 4. 用迴圈把每一筆資料印出來
for row in rows:
    region_name = row[0]  # 地區名稱
    min_temp = row[1]     # 最低溫
    max_temp = row[2]     # 最高溫
    start_time = row[3]   # 開始時間
    
    print(f"地區：{region_name} | 最低溫：{min_temp}°C | 最高溫：{max_temp}°C (時間：{start_time})")

# 5. 關閉資料庫連線
conn.close()