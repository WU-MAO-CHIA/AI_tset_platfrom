*** Settings ***
Library         Browser
Test Teardown   Close Login Page


*** Variables ***
${BASE_URL}         https://practicetestautomation.com/practice-test-login/
${USERNAME}         student
${PASSWORD}         Password123
${WRONG_USER}       wronguser
${WRONG_PASS}       wrongpassword

*** Test Cases ***
TC01 - 正常登入成功
    [Documentation]    使用正確帳號與密碼登入，驗證成功進入後台頁面
    [Tags]    login    positive
    Fill In Login Form    ${USERNAME}    ${PASSWORD}
    Wait For Elements State    text=Logged In Successfully    visible
    Wait For Elements State    text=Log out    visible

TC02 - 錯誤帳號登入失敗
    [Documentation]    使用錯誤帳號登入，驗證頁面顯示帳號錯誤提示
    [Tags]    login    negative
    Fill In Login Form    ${WRONG_USER}    ${PASSWORD}
    Wait For Elements State    id=error    visible
    Get Text    id=error    ==    Your username is invalid!

TC03 - 錯誤密碼登入失敗
    [Documentation]    使用錯誤密碼登入，驗證頁面顯示密碼錯誤提示
    [Tags]    login    negative
    Fill In Login Form    ${USERNAME}    ${WRONG_PASS}
    Wait For Elements State    id=error    visible
    Get Text    id=error    ==    Your password is invalid!

*** Keywords ***
Open Login Page
    [Documentation]    開啟瀏覽器並導向登入頁面
    New Browser     chromium    headless=True
    New Context
    New Page        ${BASE_URL}

Fill In Login Form
    [Documentation]    填寫登入表單並送出
    [Arguments]    ${username}    ${password}
    Open Login Page
    Fill Text       id=username    ${username}
    Fill Text       id=password    ${password}
    Click           id=submit

Close Login Page
    [Documentation]    關閉瀏覽器
    Close Browser
