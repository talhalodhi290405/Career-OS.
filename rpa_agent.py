from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import socket
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import TimeoutError as PlaywrightTimeoutError, async_playwright
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger("careeros.rpa")

# Initialize LLM for Agentic Decision Making
llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro")

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

async def _get_page_state(page):
    """Captures the current state of the page for the LLM to reason about."""
    content = await page.content()
    # In a production environment, we would simplify the DOM here to save tokens
    return content[:10000] # Truncated for stability

async def _execute_action(page, action_type: str, selector: str, value: str = ""):
    """Executes a specific browser action."""
    try:
        locator = page.locator(selector).first
        if action_type == "fill":
            await locator.fill(value, timeout=5000)
        elif action_type == "click":
            await locator.click(timeout=5000)
        elif action_type == "upload":
            await locator.set_input_files(value, timeout=5000)
        return True
    except Exception as e:
        logger.error(f"Action {action_type} failed on {selector}: {e}")
        return False

async def run_application_bot(
    cv_path: str,
    job_url: str,
    *,
    candidate_name: str = "",
    candidate_email: str = "",
    z_axis_approved: bool = False,
) -> dict[str, str]:
    """Agentic Browser RPA loop: Observe -> Reason -> Act."""
    if z_axis_approved is not True:
        return {"rpa_status": "blocked", "message": "Z-Axis approval is required."}

    resume = Path(cv_path).expanduser()
    if not resume.is_file() or resume.suffix.lower() != ".pdf":
        return {"rpa_status": "failed", "message": "A generated tailored CV PDF is required."}
    if not _is_public_http_url(job_url):
        return {"rpa_status": "failed", "message": "A public HTTP(S) application URL is required."}

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="CareerOS Digital FTE / 1.0 (Agentic RPA)"
            )
            page = await context.new_page()
            page.set_default_timeout(15_000)

            logger.info("Navigating to job portal: %s", job_url)
            await page.goto(job_url, wait_until="networkidle", timeout=60_000)

            # Agentic Loop
            max_iterations = 15
            for i in range(max_iterations):
                state = await _get_page_state(page)

                prompt = f"""
                You are a Job Application Agent.
                Current Page HTML snippet: {state}
                Candidate Data: Name={candidate_name}, Email={candidate_email}, ResumePath={str(resume)}

                Goal: Fill out the application form and upload the resume.
                STOP when the form is filled and only the 'Submit' button remains.

                Respond ONLY in JSON format:
                {{
                    "action": "fill" | "click" | "upload" | "done",
                    "selector": "CSS selector",
                    "value": "text to fill or path to upload",
                    "reason": "why this action"
                }}
                """

                response = await llm.ainvoke([
                    SystemMessage(content="You are a high-precision RPA agent."),
                    HumanMessage(content=prompt)
                ])

                # Parse response (assuming JSON output from LLM)
                import json
                try:
                    decision = json.loads(response.content)
                except:
                    logger.error("LLM failed to provide valid JSON. Retrying...")
                    continue

                if decision["action"] == "done":
                    break

                success = await _execute_action(
                    page,
                    decision["action"],
                    decision["selector"],
                    decision.get("value", "")
                )

                if not success:
                    logger.warning(f"Iteration {i}: Action {decision['action']} failed. Re-evaluating.")

            review_seconds = max(0, int(os.getenv("CAREEROS_RPA_REVIEW_SECONDS", "300")))
            if review_seconds:
                logger.info("Agentic preparation complete. Browser open for human review.")
                await page.wait_for_timeout(review_seconds * 1000)

            return {
                "rpa_status": "ready_for_review",
                "message": "Agentic RPA has filled the form. Please review and submit manually.",
                "current_url": page.url,
            }
    except Exception as error:
        logger.exception("Agentic Playwright failed")
        return {
            "rpa_status": "failed",
            "message": f"Agentic RPA failed: {type(error).__name__}. {str(error)}",
        }

if __name__ == "__main__":
    result = asyncio.run(
        run_application_bot("", "", z_axis_approved=False)
    )
    print(result["message"])
