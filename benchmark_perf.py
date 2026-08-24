import time
import json
from playwright.sync_api import sync_playwright

def measure_performance():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        requests_list = []

        def on_response(response):
            requests_list.append((response.status, response.url))

        page.on("response", on_response)

        t0 = time.time()
        print("--> Navigating to https://nguyentruclam.io.vn ...")
        page.goto("https://nguyentruclam.io.vn", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        total_load_time_ms = int((time.time() - t0) * 1000)

        # Performance timing metrics from window.performance
        metrics = page.evaluate("""() => {
            const nav = performance.getEntriesByType('navigation')[0] || {};
            const paint = performance.getEntriesByType('paint');
            const fcp = paint.find(p => p.name === 'first-contentful-paint');
            
            return {
                ttfb: nav.responseStart - nav.requestStart,
                domInteractive: nav.domInteractive - nav.startTime,
                domContentLoaded: nav.domContentLoadedEventEnd - nav.startTime,
                loadComplete: nav.loadEventEnd - nav.startTime,
                fcp: fcp ? fcp.startTime : null
            };
        }""")

        print("\n=== WEB PERFORMANCE METRICS ===")
        print(f"Total Requests count : {len(requests_list)}")
        print(f"TTFB                 : {metrics.get('ttfb', 0):.2f} ms")
        print(f"FCP                  : {metrics.get('fcp', 0):.2f} ms" if metrics.get('fcp') else "FCP: N/A")
        print(f"DOM Content Loaded   : {metrics.get('domContentLoaded', 0):.2f} ms")
        print(f"Full Measured Time   : {total_load_time_ms} ms")

        print(f"\n=== REQUEST LIST ({len(requests_list)} requests) ===")
        for status, url in requests_list:
            print(f"[{status}] {url}")

        browser.close()

if __name__ == "__main__":
    measure_performance()
