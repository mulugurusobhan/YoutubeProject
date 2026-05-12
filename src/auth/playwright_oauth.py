"""Playwright-based Google OAuth helper for headless VM environments.

Automates the Google OAuth consent flow using Playwright when no desktop
browser is available (e.g. on a headless Ubuntu VM).

Usage (standalone):
    python -m src.auth.playwright_oauth

Usage (from web app):
    POST /auth/playwright  {email, password}
"""

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, Browser

from ..config import PROJECT_ROOT

TOKEN_PATH = PROJECT_ROOT / "config" / "youtube_token.json"
CLIENT_SECRET_PATH = PROJECT_ROOT / "config" / "client_secret.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
]
OAUTH_REDIRECT_URI = "http://localhost:5000/auth/google/callback"
SCREENSHOTS_DIR = PROJECT_ROOT / "output" / "oauth_screenshots"


def _save_screenshot(page: Page, name: str):
    """Save a debug screenshot."""
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    path = SCREENSHOTS_DIR / f"{name}.png"
    page.screenshot(path=str(path))
    print(f"  [Screenshot] {path}")


def _build_auth_url() -> str:
    """Build the Google OAuth authorization URL from client_secret.json."""
    with open(CLIENT_SECRET_PATH) as f:
        secrets = json.load(f)

    # Support both "web" and "installed" client types
    client_info = secrets.get("web") or secrets.get("installed") or {}
    client_id = client_info["client_id"]

    from urllib.parse import urlencode

    params = {
        "client_id": client_id,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


def run_oauth_flow(email: str, password: str, flask_base_url: str = "http://localhost:5000") -> dict:
    """Run the full Google OAuth flow using Playwright.

    1. Navigates to the Flask /auth/google endpoint (or builds the URL directly)
    2. Enters Google credentials on the consent page
    3. Waits for redirect back to Flask callback
    4. Returns result status

    Args:
        email: Google account email
        password: Google account password
        flask_base_url: Base URL of the running Flask app

    Returns:
        dict with 'success' bool and 'message' str
    """
    print("[OAuth] Starting Playwright-based Google OAuth flow...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        try:
            result = _do_oauth(page, email, password, flask_base_url)
        except Exception as e:
            _save_screenshot(page, "error_final")
            result = {"success": False, "message": f"OAuth flow failed: {e}"}
        finally:
            browser.close()

    return result


def _do_oauth(page: Page, email: str, password: str, flask_base_url: str) -> dict:
    """Internal: execute each step of the OAuth flow."""

    # Step 1: Navigate to Flask's /auth/google which redirects to Google
    print("[OAuth] Step 1: Starting OAuth via Flask...")
    page.goto(f"{flask_base_url}/auth/google", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)
    _save_screenshot(page, "01_google_login_page")

    current_url = page.url
    print(f"[OAuth] Current URL: {current_url}")

    # Step 2: Enter email
    print("[OAuth] Step 2: Entering email...")
    try:
        email_input = page.locator('input[type="email"]')
        email_input.wait_for(state="visible", timeout=15000)
        email_input.fill(email)
        time.sleep(1)
        _save_screenshot(page, "02_email_entered")

        # Click Next
        next_btn = page.locator('#identifierNext, button:has-text("Next")')
        next_btn.click()
        time.sleep(3)
        _save_screenshot(page, "03_after_email_next")
    except Exception as e:
        _save_screenshot(page, "02_email_error")
        return {"success": False, "message": f"Failed to enter email: {e}"}

    # Step 3: Enter password
    print("[OAuth] Step 3: Entering password...")
    try:
        password_input = page.locator('input[type="password"]')
        password_input.wait_for(state="visible", timeout=15000)
        password_input.fill(password)
        time.sleep(1)
        _save_screenshot(page, "04_password_entered")

        # Click Next
        next_btn = page.locator('#passwordNext, button:has-text("Next")')
        next_btn.click()
        time.sleep(5)
        _save_screenshot(page, "05_after_password_next")
    except Exception as e:
        _save_screenshot(page, "04_password_error")
        return {"success": False, "message": f"Failed to enter password: {e}"}

    current_url = page.url
    print(f"[OAuth] After login, URL: {current_url}")

    # Check for 2FA / verification challenges
    if "challenge" in current_url or "signin/v2" in current_url:
        _save_screenshot(page, "06_challenge_detected")
        return {
            "success": False,
            "message": (
                "Google requires additional verification (2FA/challenge). "
                "Check output/oauth_screenshots/ for details. "
                "You may need to: 1) Disable 2FA temporarily, "
                "2) Use an App Password, or 3) Complete the challenge manually."
            ),
        }

    # Step 4: Handle consent screen (Allow/Continue)
    print("[OAuth] Step 4: Handling consent screen...")
    try:
        # Wait a moment for consent page to load
        time.sleep(3)
        _save_screenshot(page, "06_consent_page")

        # Look for "Continue" or "Allow" buttons on the consent screen
        consent_selectors = [
            'button:has-text("Continue")',
            'button:has-text("Allow")',
            '#submit_approve_access',
            'button[data-idom-class*="continue"]',
        ]

        clicked = False
        for selector in consent_selectors:
            try:
                btn = page.locator(selector)
                if btn.count() > 0 and btn.first.is_visible():
                    btn.first.click()
                    clicked = True
                    print(f"[OAuth] Clicked consent button: {selector}")
                    time.sleep(3)
                    break
            except Exception:
                continue

        if not clicked:
            # Maybe there are scope checkboxes to select first
            _save_screenshot(page, "06b_no_consent_button")
            # Try selecting all checkboxes then clicking continue
            checkboxes = page.locator('input[type="checkbox"]')
            for i in range(checkboxes.count()):
                try:
                    if not checkboxes.nth(i).is_checked():
                        checkboxes.nth(i).check()
                except Exception:
                    pass

            time.sleep(1)
            for selector in consent_selectors:
                try:
                    btn = page.locator(selector)
                    if btn.count() > 0 and btn.first.is_visible():
                        btn.first.click()
                        clicked = True
                        time.sleep(3)
                        break
                except Exception:
                    continue

        _save_screenshot(page, "07_after_consent")
    except Exception as e:
        _save_screenshot(page, "06_consent_error")
        print(f"[OAuth] Consent handling note: {e}")

    # Step 5: Wait for redirect back to Flask callback
    print("[OAuth] Step 5: Waiting for redirect to callback...")
    try:
        # Wait up to 15 seconds for the redirect
        for _ in range(15):
            current_url = page.url
            if "localhost:5000" in current_url or "127.0.0.1:5000" in current_url:
                break
            time.sleep(1)

        _save_screenshot(page, "08_final_page")
        current_url = page.url
        print(f"[OAuth] Final URL: {current_url}")

        # Check if we ended up back on the Flask app
        if "localhost:5000" in current_url or "127.0.0.1:5000" in current_url:
            # Check if token was saved
            time.sleep(2)
            if TOKEN_PATH.exists():
                print("[OAuth] Token file saved successfully!")
                return {
                    "success": True,
                    "message": "Google OAuth completed! YouTube token saved.",
                }
            else:
                return {
                    "success": True,
                    "message": "Redirected to Flask callback. Check if token was saved.",
                }
        else:
            return {
                "success": False,
                "message": (
                    f"OAuth flow did not redirect back to Flask. "
                    f"Final URL: {current_url}. "
                    f"Check output/oauth_screenshots/ for details."
                ),
            }
    except Exception as e:
        _save_screenshot(page, "08_redirect_error")
        return {"success": False, "message": f"Waiting for redirect failed: {e}"}


def main():
    """CLI entry point — prompts for credentials and runs the flow."""
    import getpass

    print("=" * 60)
    print("  Google OAuth Login (Playwright)")
    print("=" * 60)
    print()
    print("This will use Playwright to automate Google login on this VM.")
    print("Make sure the Flask web app is running (python web_app.py).")
    print()

    email = input("  Google email: ").strip()
    password = getpass.getpass("  Google password: ")

    if not email or not password:
        print("Error: Email and password are required.")
        return

    result = run_oauth_flow(email, password)
    print()
    print(f"  Result: {'SUCCESS' if result['success'] else 'FAILED'}")
    print(f"  {result['message']}")


if __name__ == "__main__":
    main()
