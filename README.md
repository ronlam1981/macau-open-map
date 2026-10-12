# 澳門開放地圖

Leaflet + OpenStreetMap，GitHub Pages 靜態網站。

39 個已接入圖層、4,063 個地點，完整目錄 1,376 個數據集。政府資料為 2026-09-20 取得的快照；API 標記代表來源提供 API，不代表即時更新。未設置自動更新排程。

來源：澳門特別行政區政府數據開放平台 https://data.gov.mo/Datasets 。地圖 © OpenStreetMap contributors。

index.html 是可直接部署的獨立網頁。非政府官方作品。停車場只有位置資訊，未接即時剩餘車位。定位只在瀏覽器處理。

## 篩選方式

依序選擇「設施分類 → 細分資料圖層 → 名稱或地址」。三者共同篩選；改分類會重設圖層並保留關鍵字。清除篩選回到全部地點。我的附近按目前結果的直線距離排序，再按一次可取消。

2026-10-12 更新篩選邏輯及無障礙公廁分類；政府資料取得日期仍是原有快照日期。

修改 `template.html`、`app.js` 或 `app.css` 後，執行 `python scripts/build.py` 和 `python scripts/validate.py`。建置會更新根目錄 `index.html`；未有獨立資料檔時使用現有首頁內的資料快照。
