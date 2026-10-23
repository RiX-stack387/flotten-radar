import asyncio, os
from playwright.async_api import async_playwright
from datetime import datetime

TARGETS = [
    "https://www.asb-nsw.de/",
    "https://www.asb-nsw.de/stellenangebote",
    "https://www.asb-nsw.de/bad-liebenzell",
    "https://www.asb-nsw.de/dienstleistungen-angebote/haus-und-mobilruf/24-hausnotruf"
]

async def run_scraper():
    print(r"  Ausgabe: Dual-Spiegelung nach C:\DefconRecht\ASB und G:\Meine Ablage\DefconRecht\ASB")
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()
    
    results = []
    for url in TARGETS:
        try:
            await page.goto(url, timeout=30000)
            title = await page.title()
            results.append(f"- [OK] {url} | Titel: {title}")
        except Exception as e:
            results.append(f"- [FEHLER] {url} | Grund: {str(e)}")
            
    await browser.close()
    await p.stop()
    
    timestamp = datetime.now().strftime("%Y-%m-%d")
    out_content = f"# ASB Nordschwarzwald Radar-Scan ({timestamp})\n\n" + "\n".join(results)
    
    os.makedirs(r"C:\DefconRecht\ASB", exist_ok=True)
    with open(r"C:\DefconRecht\ASB\ASB_Knowledge_Base_2026.md", "w", encoding="utf-8") as f:
        f.write(out_content)
    print("[SUCCESS] asb_nsw_radar.py sauber durchgelaufen.")

if __name__ == "__main__":
    asyncio.run(run_scraper())
