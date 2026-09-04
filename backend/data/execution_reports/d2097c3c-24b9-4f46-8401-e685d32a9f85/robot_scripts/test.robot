*** Settings ***
Library    Browser
Library    ${CURDIR}/../libs/CaptchaSolverLibrary.py

Suite Setup       初始化瀏覽器並開啟登入頁
Suite Teardown    關閉所有瀏覽器

*** Variables ***
${BASE_URL}           https://mma.sinopac.com/MemberPortal/Member/NextWebLogin.aspx
${ID_NUMBER}          A128514133
${USER_ID}            markwu0821
${PASSWORD}           9907mkmnK
${TIMEOUT}            20s

# 這三個欄位的 id 是 ASP.NET 每次載入頁面時隨機產生的雜湊值（例如 MMA21a3e63c...），
# 每次載入都不同，不能寫死；改用不會變動的 placeholder 屬性定位。
${LOC_ID_NUMBER}      css=input[placeholder="身分證字號(統一編號)"]
${LOC_USER_ID}        css=input[placeholder="使用者代碼"]
${LOC_PASSWORD}       css=input[placeholder="網路密碼"]
${LOC_CAPTCHA_INPUT}  css=input[placeholder="驗證碼"]
${LOC_CAPTCHA_IMG}    id=imgCode
${LOC_LOGIN_BTN}      id=MMA_Login

*** Test Cases ***
TC-001 正常登入成功
    [Documentation]    使用有效的身分證字號、使用者代號與密碼進行登入，驗證成功進入會員首頁
    [Tags]             login    smoke    TC-001
    [Setup]            導航至登入頁
    [Teardown]         測試後截圖留存

    # 等待登入表單就緒
    Wait For Elements State    ${LOC_ID_NUMBER}    visible    timeout=${TIMEOUT}
    Wait For Elements State    ${LOC_ID_NUMBER}    enabled    timeout=${TIMEOUT}

    # 填寫身分證字號
    Fill Text    ${LOC_ID_NUMBER}    ${ID_NUMBER}

    # 填寫使用者代號
    Fill Text    ${LOC_USER_ID}      ${USER_ID}

    # 填寫密碼
    Fill Text    ${LOC_PASSWORD}     ${PASSWORD}

    # 處理圖形驗證碼（頁面固定會顯示，非「如存在才處理」）
    處理圖形驗證碼

    # 點擊登入按鈕（真正可點擊的是 <a id="MMA_Login">，底層 image input 是隱藏的）
    Click    ${LOC_LOGIN_BTN}

    # 點擊後立即截圖：若登入被前端 JS 驗證擋下（例如彈出 alert 或顯示錯誤訊息），
    # 畫面會停留在原頁，這張截圖可協助判斷實際卡在哪一步，不必等到 Teardown 失敗截圖
    # 才處理（Teardown 當下瀏覽器有時已在收尾，畫面會是空白的）
    Sleep    1s
    Take Screenshot    filename=${OUTPUT DIR}/after_click_${TEST NAME}.png

    # 等待頁面跳轉完成
    Wait For Load State    load    timeout=${TIMEOUT}

    # 驗證登入成功：確認 URL 已離開登入頁
    ${current_url}=    Get Url
    Should Not Contain    ${current_url}    NextWebLogin

*** Keywords ***
初始化瀏覽器並開啟登入頁
    [Documentation]    Suite Setup：建立單一 Browser / Context / Page 並導航至登入頁
    New Browser    chromium    headless=True
    New Context
    New Page       ${BASE_URL}
    # 此頁面有持續性背景網路活動（心跳/追蹤），Wait For Load State networkidle 永遠不會
    # 觸發，一律會 timeout；改成直接等待表單欄位出現，才是真正代表頁面就緒的訊號。
    Wait For Elements State    ${LOC_ID_NUMBER}    visible    timeout=${TIMEOUT}

關閉所有瀏覽器
    [Documentation]    Suite Teardown：統一關閉所有瀏覽器實例
    Close Browser    ALL

導航至登入頁
    [Documentation]    TC Setup：每個 TC 執行前重新導航至登入頁，複用同一 Browser
    Go To    ${BASE_URL}
    Wait For Elements State    ${LOC_ID_NUMBER}    visible    timeout=${TIMEOUT}

測試後截圖留存
    [Documentation]    TC Teardown：測試失敗時自動截圖，不關閉 Browser
    IF    '${TEST STATUS}' == 'FAIL'
        Take Screenshot    filename=${OUTPUT DIR}/FAILED_${TEST NAME}.png
    END

處理圖形驗證碼
    [Documentation]    截圖驗證碼圖片後以 Claude Vision 辨識並填入
    Wait For Elements State    ${LOC_CAPTCHA_IMG}    visible    timeout=${TIMEOUT}
    ${captcha_path}=    Take Screenshot
    ...    filename=${OUTPUT DIR}/captcha_${TEST NAME}.png
    ...    selector=${LOC_CAPTCHA_IMG}
    ${captcha_text}=    Solve Captcha From File    ${captcha_path}
    Log    CAPTCHA 辨識結果：${captcha_text}    level=INFO
    Fill Text    ${LOC_CAPTCHA_INPUT}    ${captcha_text}
