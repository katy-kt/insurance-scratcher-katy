保發中心（TII）人身保險條款批次爬蟲開發紀錄

1. 導航目標與框架迷思 (v1 以前)
Situation (情境)： 初始版本爬蟲（早期 tii_pdf_downloader.py）運行後，於 WebDriverWait 尋找下拉選單元件時卡住 30 秒，最後拋出 TimeoutException 崩潰。當時推測網站使用老舊的 Frameset/Frame 隨機框架結構。

Task (任務)： 精確定位網頁結構，穿透子框架以操作險種下拉選單。

Action (行動)： * 撰寫診斷腳本 step1_diagnose_frames.py，開啟瀏覽器並印出頂層網頁的 HTML 原始碼及框架數量。

技術發現： 網頁實際並無任何 Frame 結構（框架數為 0）。崩潰主因為目標網址錯誤，將全文檢索頁（QueryFullText.aspx）誤當作商品查詢頁。

Result (結果)： 排除框架切換的邏輯誤區，將主程式目標網址修正為真正包含險種分類的商品查詢頁 Query.aspx，自動化程序順利選定選單。

2. POST 提交特性與狀態偵測失效 (v1 - v2)
Situation (情境)： 修正網址後運行 tii_health_scraper.py，程式一選完下拉選項，在使用者尚未輸入驗證碼的情況下，便直接判定「結果頁已載入」，解析出 0 筆資料並異常結束。

Task (任務)： 修正結果頁偵測時機，並實作專題所需的「未停售」勾選功能。

Action (行動)： * 透過 read_debug.py 分析快照，定位到未停售的 Checkbox 屬性為 id="endDate2"，由程式自動執行點擊。

技術發現： 該網站的查詢按鈕（id="Go2225"）是透過 JavaScript document.form1.submit() 以 POST 方式 提交。送出後網址列（URL）完全不會改變，依然停在 Query.aspx，而是直接刷新當前頁面的 DOM。舊版爬蟲因比對 URL 包含特定關鍵字，導致在初始頁面即錯誤觸發。

修正方案： 放棄等待 URL 變化的傳統邏輯，改用 DOM 元件消失偵測法：持續監控直到驗證碼輸入框（name="bmpC"）從畫面消失，且頁面出現「商品名稱」等結果表格特徵，才判定真正進入結果頁。

Result (結果)： 程式成功於選好選項後暫停，等候使用者手動填入驗證碼，點擊開始查詢且表單消失後，自動往前進行。

3. 異常 Alert 彈窗處理與重試機制 (v3)
Situation (情境)： 進入 tii_health_scraper_v3.py 測試階段，若使用者手動輸入驗證碼時填錯，網站會跳出瀏覽器原生彈出視窗 Alert: 識別碼錯誤！。此時爬蟲因未處理 Alert，會直接拋出 UnexpectedAlertPresentException 崩潰。

Task (任務)： 提高表單提交階段的容錯率，允許驗證碼填錯時能重複嘗試。

Action (行動)： * 在監控迴圈中引入 try-except 區塊，捕捉 UnexpectedAlertPresentException。

偵測到錯誤 Alert 時，自動執行 driver.switch_to.alert.accept() 將彈窗關閉，並在終端機印出提示，引導使用者在當前瀏覽器中重新輸入驗證碼。

Result (結果)： 實現驗證碼錯誤的關閉與重試機制，180 秒內使用者可無限次重試，直到輸入正確並成功載入結果列表。

4. 相對路徑拼接與本地端 SSL 憑證封鎖 (v4 - v4.1)
Situation (情境)： 成功進入結果列表後，程式識別出數百筆商品，但下載輸出全為 {'product': '...', 'reason': 'no PDF found'}，本地端未成功下載任何檔案，並在 error_log.txt 中拋出大量請求錯誤。

Task (任務)： 修正詳細頁請求路由，打通後端 HTTP 請求管線。

Action (行動)： * 運行 step4_save_result_list.py 儲存真實的列表頁 HTML 以分析超連結格式。

技術發現 1 (v4 修正)： 商品詳細頁超連結為相對路徑（如 DetailList.aspx?productId=...）。舊版程式使用字串相加，生成了 ...tii.org.twDetailList.aspx（漏掉了斜線 /），引發 404 錯誤。程式改用標準 urllib.parse.urljoin() 進行路徑對接。

技術發現 2 (v4.1 修正)： 修正網址後，後端 requests.Session() 在請求詳細頁時，因 Windows 本地端環境下的 Python CA 憑證鏈無法通過保發中心驗證，直接觸發了 SSLError。

優化改動： 在 requests 請求中強制加入 verify=False 參數以跳過 SSL 驗證，並使用 urllib3.disable_warnings() 壓制不安全請求的警告。

Result (結果)： 修正網址拼接並繞過 SSL 憑證限制，後端 requests Session 順利讀取到各商品詳細頁的 HTML 源碼。

5. 非標準 HTML 結構與 ASHX 動態下載端點 (v4.2)
Situation (情境)： 打通 HTTP 請求後，程式仍然沒有存下 PDF，反而產生了數百個 debug_detail_*.html，提示在詳細頁中無法提取超連結。

Task (任務)： 解決詳細頁內 PDF 連結無法被 BeautifulSoup 解析提取的底層問題。

Action (行動)： * 直接對產生的 debug_detail_*.html 進行文字層級的文本分析。

技術發現 1： 該網站並非點擊 .pdf 靜態檔案直連，而是透過後台處理程序 Open2.ashx?id=GUID 動態串流輸出。

技術發現 2： 詳細頁源碼中的 HTML 語法極不標準，href 屬性完全沒有使用引號包裹：

HTML
<a href=Open2.ashx?id=6323f3ea-5eb9-46bf-909c-eb581e548e27>XXXX-A.pdf</a>
這導致 BeautifulSoup 的 DOM 解析器（HTML Parser）在提取 href 屬性時全數判定為 None。

優化改動 (v4.2)： 徹底棄用 BeautifulSoup 的節點尋找邏輯，改用純文字正則表達式（Regex）直接對詳細頁的原始碼文本進行字串匹配：

Python
pdf_matches = re.findall(r'href=([^\s>]+Open2\.ashx\?id=[^\s>]+)', page_text)
同時比對標籤文字，若包含 -A.pdf 則判定為目標「保單條款」，精準存取動態端點執行下載。

Result (結果)： 順利繞過不標準 HTML 的解析缺陷，精準提取 GUID 下載端點，成功批次下載健康險的「保單條款 PDF」並正確命名存檔。

📂 版本演進摘要 (Version Summary)
tii_pdf_downloader.py (早期版本)： 錯誤存取 QueryFullText.aspx 並嘗試切換不存在的 QUERY 框架，因對象錯誤引發 Timeout 崩潰。

tii_health_scraper.py (v1 - v2)： 導向至正確的 Query.aspx，實作自動勾選未停售（endDate2），並將結果頁判定從網址監控改為「DOM 元件消失偵測」。

tii_health_scraper_v3.py： 引入 Alert 捕捉機制（UnexpectedAlertPresentException），修復驗證碼填錯時程式直接中斷崩潰的錯誤。

tii_health_scraper_v4.py： 使用 urljoin 修正詳細頁與翻頁（ResultQueryAll.aspx?page=X）路徑對接漏掉斜線（/）引發 404 的 Bug。

tii_health_scraper_v4.1.py： 於 Requests Session 中強制關閉憑證驗證（verify=False），解決 Windows 環境下的 SSL 驗證阻擋。

tii_health_scraper_v4.2.py (最終穩定版)： 棄用標準 DOM 解析，改用文字層級的 Regex 盲測抓取無引號的 Open2.ashx 動態下載連結，並精準過濾 -A.pdf 條款，成功完成海量批次下載管線。
