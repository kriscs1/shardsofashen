"""Plays the game in a headless browser (Playwright + Chromium) and saves screenshots: a check that the page loads, logs
in, draws the world and reacts to the keyboard and mouse without script errors.

  python tools/browser_check.py --url http://localhost:8080 --out <folder> [--name Tester] [--size 1600x900]"""
import argparse
import asyncio
import os
import sys


async def main():
    from playwright.async_api import async_playwright
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8080")
    p.add_argument("--out", default=".")
    p.add_argument("--name", default="Tester")
    p.add_argument("--password", default="testpass")
    p.add_argument("--size", default="1600x900")
    args = p.parse_args()
    w, h = (int(v) for v in args.size.split("x"))
    os.makedirs(args.out, exist_ok=True)
    errors = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(viewport={"width": w, "height": h})
        page.on("console", lambda m: errors.append("console %s: %s" % (m.type, m.text)) if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: errors.append("page error: %s" % e))
        await page.goto(args.url)
        await page.wait_for_function("document.getElementById('login-online').textContent.includes('online')", timeout=15000)
        await page.fill("#login-name", args.name)
        await page.fill("#login-password", args.password)
        await page.click("#login-button")
        await page.wait_for_timeout(1500)
        err = await page.text_content("#login-error")
        if err and "No character" in err:
            await page.click("#register-button")          # shows the appearance picker
            await page.wait_for_timeout(500)
            for part, n in ((1, 4), (2, 5), (3, 2)):        # hair, shirt, trousers: a swatch each
                await page.locator(".look-row").nth(part).locator(".swatch").nth(n).click()
            await page.wait_for_timeout(1200)
            await page.screenshot(path=os.path.join(args.out, "0-new-character.png"))
            await page.click("#register-button")          # makes the character
        await page.wait_for_function("document.getElementById('login').hidden && document.getElementById('loading').hidden",
                                     timeout=20000)
        await page.wait_for_timeout(3500)
        await page.screenshot(path=os.path.join(args.out, "1-world.png"))
        await page.evaluate("window.dsDebug.S.clock.day = 0.5; window.dsDebug.S.clock.at = performance.now()")
        await page.wait_for_timeout(500)
        await page.screenshot(path=os.path.join(args.out, "1b-day.png"))
        await page.mouse.move(w * 0.4, h * 0.45)
        await page.keyboard.down("ArrowRight")
        await page.wait_for_timeout(1200)
        await page.keyboard.up("ArrowRight")
        await page.wait_for_timeout(600)
        await page.screenshot(path=os.path.join(args.out, "2-walked.png"))
        await page.mouse.click(w * 0.35, h * 0.4, button="right")
        await page.wait_for_timeout(400)
        await page.screenshot(path=os.path.join(args.out, "3-menu.png"))
        await page.keyboard.press("Escape")
        await page.keyboard.press("KeyH")
        await page.wait_for_timeout(1200)
        await page.screenshot(path=os.path.join(args.out, "4-journal.png"))
        await page.keyboard.press("Digit3")
        await page.wait_for_timeout(500)
        await page.screenshot(path=os.path.join(args.out, "5-quests.png"))
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)
        await browser.close()
    print("errors:" if errors else "no script errors")
    for e in errors:
        print("  ", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
