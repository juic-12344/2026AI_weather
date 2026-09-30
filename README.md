# 🌤️ 台灣各縣市氣象互動儀表板 (Taiwan Weather Dashboard)

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 串接交通部中央氣象署 (CWA) 官方開放資料 API，呈現全台 22 縣市實時氣溫預測、降雨機率、動態高質感互動地圖與智慧生活穿著指南。

---

## ✨ 核心特色

- 📊 **四大關鍵氣象指標**：全台最高溫、最低溫、平均氣溫及降雨預警卡片。
- ⚡ **即時一鍵同步**：點擊按鈕直接調用中央氣象署 API 更新 SQLite 資料庫。
- 🗺️ **高質感 Folium 互動地圖**：全台 22 縣市天氣氣泡標籤，支援點擊展開詳細資訊與多圖資切換。
- 📈 **趨勢與排行榜圖表**：高低溫對比長條圖、降雨機率色彩漸層排行，以及各縣市 36 小時氣溫走勢圖。
- 👕 **智慧生活助手**：穿著建議、雨具提醒、戶外運動指數、日夜溫差防護。
- 📥 **資料檢視與匯出**：支援關鍵字搜尋與一鍵下載 CSV 數據報表。

---

## 🚀 本地快速啟動

1. **複製專案：**
   ```bash
   git clone <YOUR_GITHUB_REPO_URL>
   cd 923
   ```

2. **安裝依賴套件：**
   ```bash
   pip install -r requirements.txt
   ```

3. **啟動網頁應用：**
   ```bash
   streamlit run app.py
   ```
   或直接在 Windows 雙擊執行 `啟動網頁.bat`。

---

## 🌐 線上部署（Streamlit Cloud）

本專案完全支援 **Streamlit Community Cloud** 免費一鍵託管：
1. 將專案推上您的 GitHub 儲存庫。
2. 前往 [share.streamlit.io](https://share.streamlit.io/)。
3. 選擇您的儲存庫與分支，主程式填寫 `app.py`，點擊 **Deploy** 即刻上線！
