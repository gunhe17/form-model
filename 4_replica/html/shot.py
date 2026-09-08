import asyncio, sys, os
from playwright.async_api import async_playwright

D = os.path.dirname(os.path.abspath(__file__))

async def main(ids):
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        pg = await b.new_page(viewport={"width": 1004, "height": 1400})
        for i in ids:
            await pg.goto("file://" + os.path.join(D, i + ".html"))
            await pg.wait_for_timeout(250)
            await pg.screenshot(path=os.path.join(D, "shot_" + i + ".png"), full_page=True)
            n = await pg.eval_on_selector_all("[data-f]", "els=>els.length")
            print(i, "data-f=", n)
        await b.close()

asyncio.run(main(sys.argv[1:]))
