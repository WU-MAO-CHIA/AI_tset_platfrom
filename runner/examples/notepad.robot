*** Settings ***
Documentation     Windows runner 安裝後的驗證腳本：開啟記事本、輸入文字、關閉。
...               Windows 10 的傳統記事本與 Windows 11 的新版記事本，最上層視窗的 ClassName 都是 Notepad。
Library           FlaUILibrary    uia=UIA3    screenshot_on_failure=True
Test Teardown     Run Keyword And Ignore Error    Close Application By Name    notepad

*** Variables ***
${NOTEPAD}        /Window[@ClassName='Notepad']

*** Test Cases ***
Notepad Opens And Accepts Typing
    Launch Application    notepad.exe
    Wait Until Element Exist    ${NOTEPAD}    retry=20x    retry_interval=500ms
    Press Key    t'hello from AutoTest'    ${NOTEPAD}
    Element Should Exist    ${NOTEPAD}
