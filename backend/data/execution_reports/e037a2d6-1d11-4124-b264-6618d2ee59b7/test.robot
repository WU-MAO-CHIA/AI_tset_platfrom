*** Settings ***
Library    Browser

Suite Setup     Open Login Page
Suite Teardown  Close Browser

*** Variables ***
${BASE_URL}     https://mma.sinopac.com/MemberPortal/Member/NextWebLogin.aspx
${ID_NUMBER}    A128514133
${USERNAME}     markwu0821
${PASSWORD}     9907mkmnK

*** Keywords ***
Open Login Page
    New Browser    chromium    headless=True
    New Context
    New Page       ${BASE_URL}

*** Test Cases ***
TC01 正常登入成功
    [Documentation]    使用有效的身分證字號、使用者代碼與網路密碼進行登入，驗證成功進入會員頁面
    [Tags]    login    smoke    positive

    # 等待身分證字號輸入欄位出現
    Wait For Elements State    id=ContentPlaceHolder1_txtIDNo       visible    timeout=10s

    # 輸入身分證字號
    Fill Text    id=ContentPlaceHolder1_txtIDNo       ${ID_NUMBER}

    # 輸入使用者代碼
    Fill Text    id=ContentPlaceHolder1_txtMemberID   ${USERNAME}

    # 輸入網路密碼
    Fill Text    id=ContentPlaceHolder1_txtPassword   ${PASSWORD}

    # 點擊登入按鈕
    Click         id=ContentPlaceHolder1_btnLogin

    # 驗證登入成功（確認會員頁面關鍵元素出現）
    Wait For Elements State    id=ContentPlaceHolder1_lblWelcome    visible    timeout=15s