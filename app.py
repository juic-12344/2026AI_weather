import sqlite3
import datetime
import socket
import requests
import urllib3
import pandas as pd
import altair as alt
import folium
from streamlit_folium import st_folium
import streamlit as st

def get_local_ip():
    """動態取得本機在區域網路 (Wi-Fi/LAN) 中的真實 IP 位址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "10.0.12.38"

# ==========================================
# 0. 網頁基本設定與全域樣式注入 (Custom CSS)
# ==========================================
st.set_page_config(
    page_title="台灣各縣市氣象互動儀表板",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 現代科技美學與毛玻璃質感自訂樣式
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Noto+Sans+TC:wght@300;400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Outfit', 'Noto Sans TC', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* 漸層標題列 */
.main-header {
    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #00c6ff 100%);
    padding: 24px 30px;
    border-radius: 20px;
    color: white;
    box-shadow: 0 10px 25px rgba(0, 198, 255, 0.15);
    margin-bottom: 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 15px;
}

.main-header h1 {
    margin: 0;
    font-size: 2.1rem;
    font-weight: 700;
    letter-spacing: -0.5px;
    display: flex;
    align-items: center;
    gap: 12px;
}

.main-header p {
    margin: 6px 0 0 0;
    opacity: 0.9;
    font-size: 0.98rem;
}

/* 毛玻璃質感指標卡片 */
.glass-metric {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 16px;
    padding: 18px 20px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
    transition: all 0.28s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}

.glass-metric:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 28px rgba(0, 198, 255, 0.2);
    border-color: rgba(0, 198, 255, 0.4);
}

.metric-title {
    font-size: 0.88rem;
    color: #8892b0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.metric-value {
    font-size: 1.85rem;
    font-weight: 700;
    line-height: 1.2;
    margin-bottom: 4px;
}

.metric-sub {
    font-size: 0.82rem;
    color: #a0aec0;
}

/* 狀態徽章 */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
}
.badge-hot { background: rgba(239, 68, 68, 0.18); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
.badge-cold { background: rgba(59, 130, 246, 0.18); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3); }
.badge-rain { background: rgba(14, 165, 233, 0.18); color: #0ea5e9; border: 1px solid rgba(14, 165, 233, 0.3); }

/* 生活指南卡片 */
.advice-card {
    background: rgba(255, 255, 255, 0.03);
    border-left: 4px solid #00c6ff;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 14px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.06);
}

/* 按鈕美化 */
div.stButton > button:first-child {
    border-radius: 10px;
    font-weight: 600;
    transition: all 0.2s ease;
}

/* 隱藏 Streamlit 預設多餘空白 */
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# 1. 資料庫連線與 API 同步邏輯
# ==========================================
DB_FILE = "weather_data.db"
CWA_API_KEY = "CWA-B7027CBB-4D9D-415E-A5A3-737F76555BAA"

@st.cache_data(ttl=300)
def load_data():
    """從 SQLite 讀取氣象預報資料庫"""
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql("SELECT * FROM TemperatureForecasts", conn)
        conn.close()
        
        # 轉換數值格式
        for col in ["minTemp", "maxTemp", "pop"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception as e:
        st.error(f"資料庫讀取失敗：{e}")
        return pd.DataFrame()

def sync_cwa_api():
    """即時連線中央氣象署 API 更新本地 SQLite 資料庫"""
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={CWA_API_KEY}"
    try:
        res = requests.get(url, verify=False, timeout=12)
        if res.status_code == 200:
            data = res.json()
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS TemperatureForecasts")
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
            locations = data["records"]["location"]
            for loc in locations:
                region_name = loc["locationName"]
                weather_elements = loc["weatherElement"]
                wx_times = weather_elements[0]["time"]
                mint_times = weather_elements[2]["time"]
                maxt_times = weather_elements[4]["time"]
                pop_times = weather_elements[1]["time"]

                for i in range(len(wx_times)):
                    cursor.execute("""
                        INSERT INTO TemperatureForecasts (regionName, startTime, endTime, wx, minTemp, maxTemp, pop)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        region_name,
                        wx_times[i]["startTime"],
                        wx_times[i]["endTime"],
                        wx_times[i]["parameter"]["parameterName"],
                        mint_times[i]["parameter"]["parameterName"],
                        maxt_times[i]["parameter"]["parameterName"],
                        pop_times[i]["parameter"]["parameterName"]
                    ))
            conn.commit()
            conn.close()
            st.cache_data.clear()
            return True, "氣象署最新資料已成功同步更新！"
        else:
            return False, f"API 伺服器回應代碼：{res.status_code}"
    except Exception as e:
        return False, f"同步失敗：{str(e)}"

# 載入資料
df_all = load_data()

# ==========================================
# 2. 地理分區與輔助工具定義
# ==========================================
REGION_GROUPS = {
    "全台灣": [],
    "北部地區": ["基隆市", "臺北市", "台北市", "新北市", "桃園市", "新竹市", "新竹縣", "宜蘭縣"],
    "中部地區": ["苗栗縣", "臺中市", "台中市", "彰化縣", "南投縣", "雲林縣"],
    "南部地區": ["嘉義市", "嘉義縣", "臺南市", "台南市", "高雄市", "屏東縣"],
    "東部與離島": ["花蓮縣", "臺東縣", "台東縣", "澎湖縣", "金門縣", "連江縣"],
}

CITY_COORDS = {
    "基隆市": [25.1276, 121.7392], "臺北市": [25.0330, 121.5654], "台北市": [25.0330, 121.5654],
    "新北市": [25.0169, 121.4628], "桃園市": [24.9936, 121.3010], "新竹市": [24.8138, 120.9675],
    "新竹縣": [24.8387, 121.0177], "苗栗縣": [24.5602, 120.8218], "臺中市": [24.1477, 120.6736],
    "台中市": [24.1477, 120.6736], "彰化縣": [24.0517, 120.5161], "南投縣": [23.9610, 120.9719],
    "雲林縣": [23.7092, 120.4313], "嘉義市": [23.4800, 120.4491], "嘉義縣": [23.4589, 120.3204],
    "臺南市": [22.9997, 120.2270], "台南市": [22.9997, 120.2270], "高雄市": [22.6273, 120.3014],
    "屏東縣": [22.6749, 120.4879], "宜蘭縣": [24.7570, 121.7530], "花蓮縣": [23.9872, 121.6015],
    "臺東縣": [22.7554, 121.1508], "台東縣": [22.7554, 121.1508], "澎湖縣": [23.5714, 119.5793],
    "金門縣": [24.4367, 118.3164], "連江縣": [26.1595, 119.9472],
}

def get_weather_icon(wx_str: str) -> str:
    """根據天氣敘述匹配合適的 Emoji 圖示"""
    if not isinstance(wx_str, str):
        return "🌤️"
    if "雷" in wx_str:
        return "⛈️"
    elif "雨" in wx_str:
        return "🌧️"
    elif "陰" in wx_str:
        return "☁️"
    elif "多雲" in wx_str:
        return "⛅"
    elif "晴" in wx_str:
        return "☀️"
    return "🌤️"

# ==========================================
# 3. 側邊欄控制面板 (Sidebar)
# ==========================================
with st.sidebar:
    st.markdown("### ⚙️ 控制與篩選中心")
    
    # 1. 即時同步 API 按鈕
    if st.button("🔄 同步氣象署最新數據", use_container_width=True, type="primary"):
        with st.spinner("正在連線氣象署取得最新 36 小時預報..."):
            success, msg = sync_cwa_api()
            if success:
                st.toast(msg, icon="🎉")
                st.balloons()
                df_all = load_data()
            else:
                st.error(msg)
                
    st.markdown("---")
    
    # 2. 預報時段選擇
    all_times = sorted(df_all["startTime"].dropna().unique().tolist()) if not df_all.empty else []
    
    def format_time_label(t_str):
        try:
            dt = datetime.datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S")
            period = "白天 (06:00~18:00)" if dt.hour == 6 else "夜間 (18:00~06:00)"
            return f"{dt.strftime('%m/%d')} {period}"
        except:
            return t_str

    selected_time = st.selectbox(
        "📅 選擇預報時段：",
        options=all_times,
        format_func=format_time_label,
        index=0 if all_times else None,
    )
    
    # 3. 分區與縣市篩選
    selected_group = st.selectbox("🗺️ 選擇區域大分組：", list(REGION_GROUPS.keys()))
    
    if selected_group == "全台灣":
        available_cities = ["全部縣市"] + sorted(df_all["regionName"].unique().tolist())
    else:
        group_members = REGION_GROUPS[selected_group]
        available_cities = ["全部縣市"] + [c for c in group_members if c in df_all["regionName"].values]
        
    selected_city = st.selectbox("📍 鎖定特定縣市：", available_cities)
    
    st.markdown("---")
    
    # 4. 降雨預警閾值
    rain_threshold = st.slider("☔ 降雨預警標準 (%)", min_value=10, max_value=80, value=30, step=10)
    
    st.markdown("---")
    
    # 5. 手機連線指引與 QR Code
    local_ip = get_local_ip()
    mobile_url = f"http://{local_ip}:8501"
    with st.expander("📱 手機如何連線觀看？", expanded=False):
        st.markdown(f"**專屬手機網址：**\n`{mobile_url}`")
        qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=160x160&data={mobile_url}"
        st.image(qr_api, caption="手機相機掃碼開啟", width=160)
        st.markdown("""
        **必備條件：**
        1. 手機需連線到與電腦**相同的 Wi-Fi**。
        2. 請勿輸入 `localhost`（它只代表電腦本機）。
        3. 若連不上，請確保電腦防火牆未阻擋 Python。
        """)

    st.caption("資料來源：中央氣象署 CWA 36小時天氣預報")


# ==========================================
# 4. 資料過濾與統計計算
# ==========================================
if df_all.empty:
    st.warning("⚠️ 目前資料庫暫無資料，請點擊左側「🔄 同步氣象署最新數據」按鈕載入。")
    st.stop()

# 依照時段過濾
time_df = df_all[df_all["startTime"] == selected_time].copy()

# 依照區域/縣市進一步過濾
display_df = time_df.copy()
if selected_group != "全台灣":
    display_df = display_df[display_df["regionName"].isin(REGION_GROUPS[selected_group])]
if selected_city != "全部縣市":
    display_df = display_df[display_df["regionName"] == selected_city]

# 全台整體統計 (最高溫、最低溫、平均溫、最高降雨)
max_temp_row = time_df.loc[time_df["maxTemp"].idxmax()] if not time_df.empty else None
min_temp_row = time_df.loc[time_df["minTemp"].idxmin()] if not time_df.empty else None
max_pop_row = time_df.loc[time_df["pop"].idxmax()] if not time_df.empty else None
avg_temp = (time_df["maxTemp"].mean() + time_df["minTemp"].mean()) / 2 if not time_df.empty else 0


# ==========================================
# 5. 頂部主視覺 Banner
# ==========================================
formatted_time_disp = format_time_label(selected_time) if selected_time else ""
st.markdown(f"""
<div class="main-header">
    <div>
        <h1>🌤️ 台灣各縣市氣象互動儀表板</h1>
        <p>實時掌握中央氣象署 36 小時全台氣象、降雨預測與穿著生活指南 ｜ 當前預報時段：<b>{formatted_time_disp}</b></p>
    </div>
    <div>
        <span class="badge badge-rain">即時數據同步連線中</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ==========================================
# 6. 四大 KPI 指標卡片 (Top Summary Cards)
# ==========================================
k1, k2, k3, k4 = st.columns(4)

with k1:
    h_city = max_temp_row['regionName'] if max_temp_row is not None else "N/A"
    h_val = max_temp_row['maxTemp'] if max_temp_row is not None else "N/A"
    h_wx = max_temp_row['wx'] if max_temp_row is not None else ""
    st.markdown(f"""
    <div class="glass-metric">
        <div class="metric-title">🔥 全台最高溫</div>
        <div class="metric-value" style="color: #ff6b6b;">{h_val} <span style="font-size:1.1rem;">°C</span></div>
        <div class="metric-sub">{h_city} ｜ {get_weather_icon(h_wx)} {h_wx}</div>
    </div>
    """, unsafe_allow_html=True)

with k2:
    c_city = min_temp_row['regionName'] if min_temp_row is not None else "N/A"
    c_val = min_temp_row['minTemp'] if min_temp_row is not None else "N/A"
    c_wx = min_temp_row['wx'] if min_temp_row is not None else ""
    st.markdown(f"""
    <div class="glass-metric">
        <div class="metric-title">❄️ 全台最低溫</div>
        <div class="metric-value" style="color: #4dabf7;">{c_val} <span style="font-size:1.1rem;">°C</span></div>
        <div class="metric-sub">{c_city} ｜ {get_weather_icon(c_wx)} {c_wx}</div>
    </div>
    """, unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class="glass-metric">
        <div class="metric-title">🌡️ 本期全台均溫</div>
        <div class="metric-value" style="color: #20c997;">{avg_temp:.1f} <span style="font-size:1.1rem;">°C</span></div>
        <div class="metric-sub">氣候舒適度：{"舒適宜人" if 20 <= avg_temp <= 28 else ("偏涼冷" if avg_temp < 20 else "偏悶熱")}</div>
    </div>
    """, unsafe_allow_html=True)

with k4:
    r_city = max_pop_row['regionName'] if max_pop_row is not None else "N/A"
    r_val = int(max_pop_row['pop']) if max_pop_row is not None and pd.notnull(max_pop_row['pop']) else 0
    r_wx = max_pop_row['wx'] if max_pop_row is not None else ""
    st.markdown(f"""
    <div class="glass-metric">
        <div class="metric-title">☔ 最大降雨預警</div>
        <div class="metric-value" style="color: {'#38d9a9' if r_val < 30 else ('#ffd43b' if r_val < 60 else '#ff6b6b')};">{r_val} <span style="font-size:1.1rem;">%</span></div>
        <div class="metric-sub">{r_city} ｜ {"需帶雨具" if r_val >= rain_threshold else "降雨機率低"}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("") # 間距


# ==========================================
# 7. 主分頁架構 (Tabs)
# ==========================================
tab_overview, tab_map, tab_life, tab_table = st.tabs([
    "📊 氣溫圖表與趨勢對比",
    "🗺️ 互動氣象地圖",
    "👕 智慧生活與穿著指南",
    "📋 詳細資料檢視與匯出",
])

# ------------------------------------------
# TAB 1: 圖表與趨勢分析
# ------------------------------------------
with tab_overview:
    col_chart_left, col_chart_right = st.columns([3, 2])
    
    with col_chart_left:
        st.subheader("📈 各縣市高低溫區間對比圖")
        if not display_df.empty:
            melt_df = display_df.melt(
                id_vars=["regionName", "wx"],
                value_vars=["minTemp", "maxTemp"],
                var_name="溫度類型",
                value_name="溫度"
            )
            melt_df["溫度類型標籤"] = melt_df["溫度類型"].map({"minTemp": "最低溫", "maxTemp": "最高溫"})
            
            chart = alt.Chart(melt_df).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                x=alt.X("regionName:N", title="縣市行政區", sort=None, axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("溫度:Q", title="氣溫 (°C)", scale=alt.Scale(zero=False)),
                color=alt.Color(
                    "溫度類型標籤:N",
                    scale=alt.Scale(domain=["最低溫", "最高溫"], range=["#3b82f6", "#ef4444"]),
                    legend=alt.Legend(title="指標")
                ),
                xOffset="溫度類型標籤:N",
                tooltip=[
                    alt.Tooltip("regionName:N", title="地區"),
                    alt.Tooltip("溫度類型標籤:N", title="溫度類型"),
                    alt.Tooltip("溫度:Q", title="攝氏溫度 (°C)"),
                    alt.Tooltip("wx:N", title="天氣狀況"),
                ]
            ).properties(height=380)
            
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("查無符合條件的數據。")

    with col_chart_right:
        st.subheader("☔ 降雨機率排行榜 (%)")
        if not display_df.empty:
            rain_df = display_df[["regionName", "pop", "wx"]].dropna().sort_values(by="pop", ascending=True)
            
            rain_chart = alt.Chart(rain_df).mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5).encode(
                y=alt.Y("regionName:N", title="", sort="-x"),
                x=alt.X("pop:Q", title="降雨機率 (%)", scale=alt.Scale(domain=[0, 100])),
                color=alt.Color(
                    "pop:Q",
                    scale=alt.Scale(domain=[0, 30, 70, 100], range=["#6ee7b7", "#38bdf8", "#818cf8", "#f43f5e"]),
                    legend=None
                ),
                tooltip=[
                    alt.Tooltip("regionName:N", title="地區"),
                    alt.Tooltip("pop:Q", title="降雨機率 (%)"),
                    alt.Tooltip("wx:N", title="預測天氣"),
                ]
            ).properties(height=380)
            
            st.altair_chart(rain_chart, use_container_width=True)
            
    # 若選定單一縣市，加碼呈現 36 小時多時段趨勢折線圖
    if selected_city != "全部縣市":
        st.markdown("---")
        st.subheader(f"⏱️ 【{selected_city}】未來 36 小時氣溫走勢圖")
        city_history_df = df_all[df_all["regionName"] == selected_city].copy().sort_values(by="startTime")
        
        if not city_history_df.empty:
            city_history_df["時段名稱"] = city_history_df["startTime"].apply(format_time_label)
            city_history_melt = city_history_df.melt(
                id_vars=["時段名稱", "wx", "pop"],
                value_vars=["minTemp", "maxTemp"],
                var_name="溫度類型",
                value_name="溫度"
            )
            city_history_melt["溫度類型標籤"] = city_history_melt["溫度類型"].map({"minTemp": "最低溫", "maxTemp": "最高溫"})
            
            line_chart = alt.Chart(city_history_melt).mark_line(point=alt.OverlayMarkDef(size=80, filled=True)).encode(
                x=alt.X("時段名稱:N", title="預報時段", sort=None),
                y=alt.Y("溫度:Q", title="溫度 (°C)", scale=alt.Scale(zero=False)),
                color=alt.Color("溫度類型標籤:N", scale=alt.Scale(domain=["最低溫", "最高溫"], range=["#3b82f6", "#ef4444"])),
                tooltip=[
                    alt.Tooltip("時段名稱:N", title="時段"),
                    alt.Tooltip("溫度類型標籤:N", title="項目"),
                    alt.Tooltip("溫度:Q", title="氣溫 (°C)"),
                    alt.Tooltip("wx:N", title="天氣"),
                    alt.Tooltip("pop:Q", title="降雨率 (%)"),
                ]
            ).properties(height=260)
            
            st.altair_chart(line_chart, use_container_width=True)


# ------------------------------------------
# TAB 2: 高質感 Folium 互動地圖
# ------------------------------------------
with tab_map:
    col_map_top, col_map_ctrl = st.columns([3, 1])
    with col_map_top:
        st.subheader("🗺️ 台灣各縣市氣象實況分佈圖")
        st.caption("即時顯示全台 22 縣市天氣氣溫標籤，點擊可展開詳細氣象卡片與降雨量進度條。")
    with col_map_ctrl:
        map_style = st.selectbox(
            "🗺️ 地圖風格切換：",
            ["標準地圖 (OpenStreetMap)", "簡約街道 (Esri Streets)", "衛星影像 (Esri Satellite)", "淡雅灰階 (Esri Gray)"]
        )

    tile_options = {
        "標準地圖 (OpenStreetMap)": {
            "tiles": "OpenStreetMap",
            "attr": None
        },
        "簡約街道 (Esri Streets)": {
            "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
            "attr": "Esri"
        },
        "衛星影像 (Esri Satellite)": {
            "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            "attr": "Esri"
        },
        "淡雅灰階 (Esri Gray)": {
            "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
            "attr": "Esri"
        },
    }
    
    current_tile = tile_options.get(map_style, tile_options["標準地圖 (OpenStreetMap)"])

    # 自動計算地圖中心與縮放等級 (避免使用者選了特定縣市後地圖偏掉或找不到)
    if selected_city != "全部縣市" and selected_city in CITY_COORDS:
        map_center = CITY_COORDS[selected_city]
        zoom_level = 10
    elif selected_group != "全台灣":
        group_cities = [c for c in REGION_GROUPS[selected_group] if c in CITY_COORDS]
        if group_cities:
            avg_lat = sum(CITY_COORDS[c][0] for c in group_cities) / len(group_cities)
            avg_lon = sum(CITY_COORDS[c][1] for c in group_cities) / len(group_cities)
            map_center = [avg_lat, avg_lon]
            zoom_level = 9
        else:
            map_center = [23.85, 120.95]
            zoom_level = 8
    else:
        map_center = [23.85, 120.95]
        zoom_level = 8

    # 建立地圖實體 (使用免 API Key 的高穩定圖資)
    m = folium.Map(
        location=map_center,
        zoom_start=zoom_level,
        tiles=current_tile["tiles"],
        attr=current_tile["attr"]
    )

    # 呈現所有縣市（讓全台氣象一覽無遺，若有選定縣市則重點發光標記）
    for _, row in time_df.iterrows():
        c_name = row["regionName"]
        if c_name in CITY_COORDS:
            lat, lon = CITY_COORDS[c_name]
            wx = row.get("wx", "無資料")
            min_t = row.get("minTemp", "N/A")
            max_t = row.get("maxTemp", "N/A")
            pop_v = row.get("pop", 0)
            icon_emoji = get_weather_icon(wx)
            
            is_targeted = (c_name == selected_city)
            is_in_group = (selected_group == "全台灣" or c_name in REGION_GROUPS[selected_group])

            # 色彩邏輯：依氣溫與降雨
            if pop_v >= 50:
                bg_color = "#0284c7"
            elif max_t >= 32:
                bg_color = "#dc2626"
            elif max_t >= 28:
                bg_color = "#ea580c"
            else:
                bg_color = "#16a34a"

            # 樣式強化：若為選定目標，加入發光框線與放大
            if is_targeted:
                pill_border = "3px solid #ff007f; box-shadow: 0 0 15px #ff007f;"
                transform_style = "transform: translate(-50%, -50%) scale(1.22); z-index: 999;"
            elif not is_in_group:
                pill_border = "1px solid rgba(255, 255, 255, 0.4);"
                transform_style = "transform: translate(-50%, -50%) scale(0.9); opacity: 0.55;"
            else:
                pill_border = "1px solid rgba(255, 255, 255, 0.85);"
                transform_style = "transform: translate(-50%, -50%) scale(1.0);"

            # 自訂 HTML 氣象氣泡膠囊標籤
            pill_html = f"""
            <div style="
                {transform_style}
                background: {bg_color};
                color: white;
                padding: 3px 8px;
                border-radius: 14px;
                font-size: 11px;
                font-weight: 700;
                font-family: 'Outfit', 'Noto Sans TC', sans-serif;
                border: {pill_border}
                box-shadow: 0 3px 10px rgba(0,0,0,0.3);
                white-space: nowrap;
                display: flex;
                align-items: center;
                gap: 3px;
                cursor: pointer;
            ">
                <span>{icon_emoji}</span>
                <span>{c_name}</span>
                <span style="background: rgba(0,0,0,0.22); padding: 0 4px; border-radius: 6px;">{max_t}°</span>
            </div>
            """

            popup_html = f"""
            <div style="font-family: 'Outfit', 'Noto Sans TC', sans-serif; width: 190px; padding: 6px;">
                <div style="font-size: 1.15rem; font-weight: bold; border-bottom: 2px solid #00c6ff; padding-bottom: 4px; margin-bottom: 8px;">
                    {icon_emoji} {c_name}
                </div>
                <div style="margin-bottom: 4px; font-size: 0.95rem;"><b>天氣概況：</b> {wx}</div>
                <div style="margin-bottom: 4px; font-size: 0.95rem;"><b>氣溫區間：</b> <span style="color:#ef4444; font-weight:bold;">{max_t}°C</span> ~ <span style="color:#3b82f6; font-weight:bold;">{min_t}°C</span></div>
                <div style="margin-bottom: 6px; font-size: 0.95rem;"><b>降雨機率：</b> <b>{pop_v}%</b></div>
                <div style="background: #e2e8f0; border-radius: 10px; height: 8px; width: 100%; overflow: hidden;">
                    <div style="background: #0284c7; width: {min(pop_v, 100)}%; height: 100%;"></div>
                </div>
            </div>
            """

            folium.Marker(
                [lat, lon],
                popup=folium.Popup(popup_html, max_width=230),
                tooltip=f"{c_name}: {icon_emoji} {wx} ({min_t}~{max_t}°C ｜ 降雨率 {pop_v}%)",
                icon=folium.DivIcon(html=pill_html),
            ).add_to(m)

    st_folium(m, use_container_width=True, height=580, returned_objects=[])


# ------------------------------------------
# TAB 3: 智慧生活與穿著指南 (AI Weather Assistant)
# ------------------------------------------
with tab_life:
    st.subheader("💡 智慧氣象生活與出門防護指南")
    
    # 決定參考地區
    target_city = selected_city if selected_city != "全部縣市" else "臺北市"
    target_row = time_df[time_df["regionName"] == target_city]
    
    if not target_row.empty:
        t_data = target_row.iloc[0]
        cur_min = t_data["minTemp"]
        cur_max = t_data["maxTemp"]
        cur_pop = t_data["pop"]
        cur_wx = t_data["wx"]
        cur_avg = (cur_min + cur_max) / 2
        temp_diff = cur_max - cur_min

        st.info(f"📍 目前分析參考目標：**{target_city}**（天氣：{get_weather_icon(cur_wx)} {cur_wx} ｜ 氣溫：{cur_min}°C ~ {cur_max}°C ｜ 降雨率：{cur_pop}%）")
        
        g1, g2 = st.columns(2)
        
        with g1:
            # 穿著建議
            if cur_avg >= 28:
                cloth_title = "👕 建議穿著：輕便透氣短袖"
                cloth_desc = "天氣炎熱，請選擇排汗透氣的純棉短袖、短褲或洋裝，並多補充水分避免中暑！"
            elif cur_avg >= 23:
                cloth_title = "🌤️ 建議穿著：舒適薄長袖 / 針織衫"
                cloth_desc = "氣溫溫和宜人，單穿薄長袖或短袖外搭一件薄襯衫最為理想。"
            elif cur_avg >= 18:
                cloth_title = "🧥 建議穿著：防風休閒外套 / 連帽衫"
                cloth_desc = "稍有涼意，建議長袖內搭搭配夾克、風衣或針織毛衣。"
            else:
                cloth_title = "🧣 建議穿著：保暖冬裝 / 羽絨外套"
                cloth_desc = "氣溫偏冷，請備妥發熱衣、厚毛衣與羽絨外套，注意頭部與頸部保暖。"
                
            st.markdown(f"""
            <div class="advice-card">
                <h4>{cloth_title}</h4>
                <p>{cloth_desc}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 雨具提醒
            if cur_pop >= 60:
                rain_title = "☔ 必備大雨傘或雨衣"
                rain_desc = f"降雨機率高達 {cur_pop}%，外出請攜帶堅固雨具，駕駛車輛務必減速慢行防打滑。"
            elif cur_pop >= 30:
                rain_title = "🌂 建議攜帶折疊傘"
                rain_desc = f"降雨機率為 {cur_pop}%，可能有局部短暫陣雨，隨身放一把折疊傘以備不時之需。"
            else:
                rain_title = "☀️ 出門免帶傘"
                rain_desc = f"降雨機率僅 {cur_pop}%，天氣相對穩定，適合戶外休閒！"

            st.markdown(f"""
            <div class="advice-card">
                <h4>{rain_title}</h4>
                <p>{rain_desc}</p>
            </div>
            """, unsafe_allow_html=True)

        with g2:
            # 戶外運動與活動指數
            if cur_pop >= 70 or "雷" in cur_wx:
                sport_title = "🏋️ 戶外運動：不推薦（宜轉向室內）"
                sport_desc = "預期有明顯降雨或雷陣雨風險，建議選擇健身房或居家室內運動。"
            elif cur_max >= 33:
                sport_title = "⚠️ 戶外運動：注意防曬防熱傷害"
                sport_desc = "氣溫偏高，避免正午 11:00~14:00 長時間暴曬劇烈運動，適時補充電解質。"
            else:
                sport_title = "🏃 戶外運動：極為適合"
                sport_desc = "氣候舒適度良好，非常適合慢跑、騎乘自行車或戶外登山散步！"
                
            st.markdown(f"""
            <div class="advice-card">
                <h4>{sport_title}</h4>
                <p>{sport_desc}</p>
            </div>
            """, unsafe_allow_html=True)

            # 溫差警示
            if temp_diff >= 6:
                diff_title = f"🌡️ 日夜溫差警訊：高達 {temp_diff:.1f}°C"
                diff_desc = "早晚溫差顯著，建議採用洋蔥式多層次穿搭，方便隨時穿脫防感冒。"
            else:
                diff_title = f"🌡️ 溫差穩定：溫差僅 {temp_diff:.1f}°C"
                diff_desc = "整日氣溫起伏不大，體感舒適平穩。"

            st.markdown(f"""
            <div class="advice-card">
                <h4>{diff_title}</h4>
                <p>{diff_desc}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("查無此縣市資訊。")


# ------------------------------------------
# TAB 4: 詳細數據表格與匯出 (Data & Export)
# ------------------------------------------
with tab_table:
    st.subheader("📋 氣象預報詳細資料清單")
    
    # 關鍵字即時搜尋
    search_keyword = st.text_input("🔍 快速搜尋縣市或天氣狀態（例如：臺北、陣雨、晴）：", "")
    
    table_view_df = display_df.copy()
    if search_keyword:
        table_view_df = table_view_df[
            table_view_df["regionName"].str.contains(search_keyword, case=False, na=False) |
            table_view_df["wx"].str.contains(search_keyword, case=False, na=False)
        ]
        
    # 美化呈現表格
    table_view_df = table_view_df.rename(columns={
        "regionName": "縣市行政區",
        "startTime": "預報起始時間",
        "endTime": "預報結束時間",
        "wx": "天氣狀態",
        "minTemp": "最低氣溫 (°C)",
        "maxTemp": "最高氣溫 (°C)",
        "pop": "降雨機率 (%)"
    })
    
    # 計算溫差欄位
    if "最高氣溫 (°C)" in table_view_df.columns and "最低氣溫 (°C)" in table_view_df.columns:
        table_view_df["溫差 (°C)"] = table_view_df["最高氣溫 (°C)"] - table_view_df["最低氣溫 (°C)"]

    display_cols = ["縣市行政區", "天氣狀態", "最低氣溫 (°C)", "最高氣溫 (°C)", "溫差 (°C)", "降雨機率 (%)", "預報起始時間", "預報結束時間"]
    show_df = table_view_df[[c for c in display_cols if c in table_view_df.columns]].reset_index(drop=True)
    show_df.index = range(1, len(show_df) + 1)
    
    st.dataframe(show_df, use_container_width=True, height=420)
    
    # 資料下載按鈕
    csv_bytes = show_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 下載當前篩選數據報表 (CSV)",
        data=csv_bytes,
        file_name=f"taiwan_weather_forecast_{datetime.date.today()}.csv",
        mime="text/csv",
    )


# ==========================================
# 8. 頁尾版權與宣告
# ==========================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #8892b0; font-size: 0.85rem; padding: 10px;">
    🌤️ 台灣各縣市氣象互動儀表板 ｜ 資料介接：交通部中央氣象署 Open Data API (F-C0032-001) ｜ 支援即時動態更新
</div>
""", unsafe_allow_html=True)