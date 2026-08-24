from playwright.sync_api import sync_playwright

def test_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Login
        page.goto("http://localhost:5173" if False else "http://localhost:8000")
        page.fill("input[type='email']", "admin@nguyentruclam.io.vn")
        page.fill("input[type='password']", "Truc@1905s")
        page.click("button[type='submit']")
        page.wait_for_timeout(2000)

        # Go to Rules Tab
        page.click("text=Rules")
        page.wait_for_timeout(1000)

        # Screenshot
        page.screenshot(path="rules_tab.png", full_page=True)
        
        # Try adding an app rule
        page.select_option("select", "app")
        page.fill("input[placeholder='e.g. game.exe']", "test_playwright.exe")
        page.click("button:has-text('Thêm Rule')")
        page.wait_for_timeout(1000)

        # Screenshot again
        page.screenshot(path="rules_tab_after.png", full_page=True)

        browser.close()

if __name__ == "__main__":
    test_ui()
