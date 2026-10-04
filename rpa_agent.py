from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import socket
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import TimeoutError as PlaywrightTimeoutError, async_playwright


logger = logging.getLogger("careeros.rpa")


def _is_public_http_url(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            return False
        host = parsed.hostname.lower().rstrip(".")
        if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
            return False
        try:
            addresses = {ipaddress.ip_address(host)}
        except ValueError:
            addresses = {
                ipaddress.ip_address(record[4][0])
                for record in socket.getaddrinfo(
                    host, parsed.port or (443 if parsed.scheme == "https" else 80),
                    type=socket.SOCK_STREAM,
                )
            }
        return bool(addresses) and all(address.is_global for address in addresses)
    except (ValueError, OSError):
        return False


async def _fill_first(page, selectors: list[str], value: str) -> bool:
    if not value:
        return False
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if await locator.count() and await locator.is_visible(timeout=500):
                await locator.fill(value, timeout=2_000)
                return True
        except PlaywrightTimeoutError:
            continue
    return False


async def run_application_bot(
    cv_path: str,
    job_url: str,
    *,
    candidate_name: str = "",
    candidate_email: str = "",
    z_axis_approved: bool = False,
) -> dict[str, str]:
    """Prepare a public application form and stop before its submit control."""
    if z_axis_approved is not True:
        return {"rpa_status": "blocked", "message": "Z-Axis approval is required."}

    resume = Path(cv_path).expanduser()
    if not resume.is_file() or resume.suffix.lower() != ".pdf":
        return {"rpa_status": "failed", "message": "A generated tailored CV PDF is required."}
    if not _is_public_http_url(job_url):
        return {"rpa_status": "failed", "message": "A public HTTP(S) application URL is required."}

    name_parts = candidate_name.strip().split(maxsplit=1)
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=False)
            page = await browser.new_page()
            page.set_default_timeout(5_000)
            await page.goto(job_url, wait_until="domcontentloaded", timeout=30_000)

            text_inputs = page.locator('input[type="text"]')
            count = await text_inputs.count()
            if count > 0 and first_name:
                await text_inputs.nth(0).fill(first_name)
            if count > 1 and last_name:
                await text_inputs.nth(1).fill(last_name)
            await _fill_first(
                page,
                [
                    'input[autocomplete="given-name"]',
                    'input[name*="first" i]',
                    'input[id*="first" i]',
                ],
                first_name,
            )
            await _fill_first(
                page,
                [
                    'input[autocomplete="family-name"]',
                    'input[name*="last" i]',
                    'input[id*="last" i]',
                ],
                last_name,
            )
            await _fill_first(
                page,
                [
                    'input[type="email"]',
                    'input[autocomplete="email"]',
                    'input[name*="email" i]',
                ],
                candidate_email,
            )
            file_inputs = page.locator('input[type="file"]')
            if not await file_inputs.count():
                return {"rpa_status": "failed", "message": "No CV upload field was found."}
            await file_inputs.first.set_input_files(str(resume))

            review_seconds = max(0, int(os.getenv("CAREEROS_RPA_REVIEW_SECONDS", "120")))
            if review_seconds:
                logger.info("Application prepared; browser remains open for human review.")
                await page.wait_for_timeout(review_seconds * 1000)
            return {
                "rpa_status": "ready_for_review",
                "message": "Fields filled and CV attached. Nothing was submitted; review the open browser form.",
                "current_url": page.url,
            }
    except Exception as error:
        logger.exception("Playwright application preparation failed")
        return {
            "rpa_status": "failed",
            "message": f"Application preparation failed: {type(error).__name__}.",
        }


if __name__ == "__main__":
    result = asyncio.run(
        run_application_bot("", "", z_axis_approved=False)
    )
    print(result["message"])