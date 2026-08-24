from playwright.sync_api import sync_playwright

def test_ui_html():
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

        html = page.content()
        with open("page_html.txt", "w", encoding="utf-8") as f:
            f.write(html)
        
        browser.close()

if __name__ == "__main__":
    test_ui_html()
