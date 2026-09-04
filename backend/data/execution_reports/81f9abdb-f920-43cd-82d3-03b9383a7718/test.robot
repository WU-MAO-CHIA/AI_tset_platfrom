*** Settings ***
Library    Browser
Library    ${CURDIR}/../libs/CaptchaSolverLibrary.py

Suite Setup       初始化瀏覽器並開啟登入頁
Suite Teardown    關閉所有瀏覽器

*** Variables ***
${BASE_URL}           https://mma.sinopac.com/MemberPortal/Member/NextWebLogin.aspx
${ID_NUMBER}          A128514133
${USER_ID}            markwu0821
${PASSWORD}           99907mkmnK
${TIMEOUT}            20s
${SUCCESS_LOCATOR}    id=ContentPlaceHolder1_lblWelcome

*** Test Cases ***
TC-001 正常登入成功
    [Documentation]    使用有效的身分證字號、使用者代號與密碼進行登入，驗證成功進入會員首頁
    [Tags]             login    smoke    TC-001
    [Setup]            導航至登入頁
    [Teardown]         測試後截圖留存

    # 等待登入表單就緒
    Wait For Elements State    id=ContentPlaceHolder1_txtIDNo    visible    timeout=${TIMEOUT}

    # 填寫身分證字號
    Fill Text    id=ContentPlaceHolder1_txtIDNo        ${ID_NUMBER}

    # 填寫使用者代號
    Fill Text    id=ContentPlaceHolder1_txtUserID      ${USER_ID}

    # 填寫密碼
    Fill Text    id=ContentPlaceHolder1_txtPassword    ${PASSWORD}

    # 處理圖形驗證碼（如存在）
    處理圖形驗證碼（如存在）

    # 點擊登入按鈕
    Click    id=ContentPlaceHolder1_btnLogin

    # 驗證登入成功：等待頁面跳轉並確認歡迎元素出現
    Wait For Load State       networkidle    timeout=${TIMEOUT}
    Wait For Elements State   ${SUCCESS_LOCATOR}    visible    timeout=${TIMEOUT}

    # 額外確認 URL 已離開登入頁
    ${current_url}=    Get Url
    Should Not Contain    ${current_url}    NextWebLogin
    ...    msg=URL 仍停留在登入頁，登入未成功跳轉

*** Keywords ***
初始化瀏覽器並開啟登入頁
    [Documentation]    Suite Setup：建立單一 Browser / Context / Page 並導航至登入頁
    New Browser    chromium    headless=False
    New Context    viewport={'width': 1280, 'height': 800}
    New Page       ${BASE_URL}
    Wait For Load State       networkidle    timeout=${TIMEOUT}
    Wait For Elements State
    ...    id=ContentPlaceHolder1_txtIDNo
    ...    visible
    ...    timeout=${TIMEOUT}

關閉所有瀏覽器
    [Documentation]    Suite Teardown：關閉所有瀏覽器實例
    Close Browser    ALL

導航至登入頁
    [Documentation]    TC Setup：每個 TC 執行前重新導航至登入頁（複用同一 Browser）
    Go To    ${BASE_URL}
    Wait For Load State       networkidle    timeout=${TIMEOUT}
    Wait For Elements State
    ...    id=ContentPlaceHolder1_txtIDNo
    ...    visible
    ...    timeout=${TIMEOUT}

測試後截圖留存
    [Documentation]    TC Teardown：失敗時截圖留存，不關閉 Browser
    Run Keyword If Test Failed
    ...    Take Screenshot    filename=${OUTPUT DIR}/FAILED_${TEST NAME}.png

處理圖形驗證碼（如存在）
    [Documentation]    若頁面存在圖形驗證碼，截圖後以 Claude Vision 辨識並填入
    ${captcha_visible}=    Run Keyword And Return Status
    ...    Wait For Elements State
    ...    id=ContentPlaceHolder1_imgCaptcha
    ...    visible
    ...    timeout=3s

    IF    ${captcha_visible}
        ${captcha_path}=    Take Screenshot
        ...    filename=${OUTPUT DIR}/captcha_${TEST NAME}.png
        ...    selector=id=ContentPlaceHolder1_imgCaptcha
        ${captcha_text}=    Solve Captcha From File    ${captcha_path}
        Log    CAPTCHA 辨識結果：${captcha_text}    level=INFO
        Wait For Elements State
        ...    id=ContentPlaceHolder1_txtCaptcha
        ...    visible
        ...    timeout=3s
        Fill Text    id=ContentPlaceHolder1_txtCaptcha    ${captcha_text}
    END