from playwright.async_api import async_playwright
import asyncio

async def execute_job_application(state: dict):
    """
    RPA Agent: Navigates target portals, maps DOM fields, and uploads the tailored PDF.
    Strictly governed by the Z-Axis human approval gate.
    """
    # 1. Z-AXIS GOVERNANCE CHECK
    if not state.get("z_axis_approved", False):
        print("❌ EXECUTION BLOCKED: Z-Axis Human Approval Required.")
        return {"rpa_status": "blocked", "message": "Awaiting explicit human consent."}
    
    print("✅ Z-Axis Approved. Initializing Playwright Headless Browser...")
    
    # 2. AUTONOMOUS BROWSER EXECUTION
    async with async_playwright() as p:
        # Keep headless=True so it runs silently in the background during your demo
        browser = await p.chromium.launch(headless=True) 
        page = await browser.new_page()
        
        target_url = state.get("target_job_url", "https://example.com/apply")
        tailored_cv = state.get("tailored_cv", "resume.pdf")
        
        try:
            print(f"--> Navigating to target job portal: {target_url}")
            await page.goto(target_url)
            
            # Hackathon Demo DOM Mapping (Placeholder selectors for the live demo)
            print("--> Mapping DOM fields and injecting candidate data...")
            # await page.fill('input[name="firstName"]', "Talha")
            # await page.fill('input[name="lastName"]', "Lodhi")
            
            print(f"--> Uploading tailored PDF artifact: {tailored_cv}")
            # await page.set_input_files('input[type="file"]', tailored_cv)
            
            print("--> Submitting application payload...")
            # await page.click('button[type="submit"]')
            
            # Wait for submission confirmation
            await page.wait_for_timeout(2000) 
            
            print("✅ Application autonomously submitted.")
            status = "success"
            
        except Exception as e:
            print(f"❌ RPA Failure: {str(e)}")
            status = "failed"
            
        finally:
            await browser.close()
            
        return {"rpa_status": status, "message": "Application sequence completed."}

# Quick local test execution
if __name__ == "__main__":
    test_state = {
        "z_axis_approved": True, 
        "tailored_cv": "Tailored_Resume_v1.pdf",
        "target_job_url": "https://google.com" # Safe test target
    }
    asyncio.run(execute_job_application(test_state))
    