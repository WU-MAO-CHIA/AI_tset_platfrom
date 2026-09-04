*** Settings ***
Library    Browser
Library    ${CURDIR}/../libs/CaptchaSolverLibrary.py

Suite Setup       Open Login Page
Suite Teardown    Close Browser

*** Variables ***
${BASE_URL}       https://mma.sinopac.com/MemberPortal/Member/NextWebLogin.aspx
${ID_NUMBER}      A128514133
${USER_ID}        markwu0821
${PASSWORD}       99907mkmnK

*** Test Cases ***
TC-001 正常登入成功
    [Documentation]    使用有效的身分證字號、使用者代號與密碼進行登入，驗證成功進入會員首頁
    [Tags]    login    smoke    TC-001
    [Setup]    Navigate To Login Page
    [Teardown]    Close Browser

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

    # 驗證登入成功（確認會員首頁元素出現）
    Wait For Elements State    role=heading    visible    timeout=10s

*** Keywords ***
Open Login Page
    New Browser    chromium    headless=True
    New Context
    New Page       ${BASE_URL}

Navigate To Login Page
    New Browser    chromium    headless=True
    New Context
    New Page       ${BASE_URL}

處理圖形驗證碼（如存在）
    [Documentation]    若頁面存在圖形驗證碼，截圖後以 Claude Vision 辨識並填入
    ${captcha_visible}=    Run Keyword And Return Status
    ...    Wait For Elements State    id=ContentPlaceHolder1_imgCaptcha    visible    timeout=3s
    IF    ${captcha_visible}
        ${captcha_path}=    Take Screenshot
        ...    filename=${OUTPUT DIR}/captcha_${TEST NAME}.png
        ...    selector=id=ContentPlaceHolder1_imgCaptcha
        ...    fullPage=False
        ${captcha_text}=    Solve Captcha From File    ${captcha_path}
        Log    CAPTCHA 辨識結果：${captcha_text}
        Fill Text    id=ContentPlaceHolder1_txtCaptcha    ${captcha_text}
    END