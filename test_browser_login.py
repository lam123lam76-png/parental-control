import time
import json
from playwright.sync_api import sync_playwright

def run_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        console_logs = []
        network_errors = []
        network_all = []

        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("response", lambda resp: network_all.append(f"RESP {resp.status} {resp.url}"))

        print("--> Navigating to https://nguyentruclam.io.vn ...")
        page.goto("https://nguyentruclam.io.vn", wait_until="networkidle")
        time.sleep(2)

        print("--> Checking initial state...")
        email_inputs = page.locator('input[type="email"]').all()
        password_inputs = page.locator('input[type="password"]').all()

        if len(email_inputs) > 0 and len(password_inputs) > 0:
            print("--> Filling login form...")
            email_inputs[0].fill("admin@nguyentruclam.io.vn")
            password_inputs[0].fill("Truc@1905s")
            
            # Click the submit button specifically
            submit_btn = page.locator('button[type="submit"]').first
            print("--> Submitting login form...")
            submit_btn.click()
            
            # Wait for dashboard to mount
            print("--> Waiting for dashboard to mount...")
            page.wait_for_timeout(4000)
            page.screenshot(path="C:/Users/admin/.gemini/antigravity/brain/31ec012c-2a6f-4d2d-9387-a2966ddc948a/browser_step2_logged_in.png", full_page=True)

        # Polling for 6 seconds
        print("--> Polling for 6 seconds...")
        page.wait_for_timeout(6000)
        page.screenshot(path="C:/Users/admin/.gemini/antigravity/brain/31ec012c-2a6f-4d2d-9387-a2966ddc948a/browser_step3_live.png", full_page=True)

        # Extract localStorage
        local_storage = page.evaluate("() => ({ ...localStorage })")
        print("\n=== LOCAL STORAGE STATE ===")
        for k, v in local_storage.items():
            print(f"  {k}: {str(v)[:40]}..." if len(str(v)) > 40 else f"  {k}: {v}")

        print("\n=== CONSOLE LOGS ===")
        for log in console_logs:
            print(log)

        print("\n=== ALL NETWORK RESPONSES ===")
        for resp in network_all:
            if "/api/" in resp:
                print(resp)

        browser.close()

if __name__ == "__main__":
    run_test()
