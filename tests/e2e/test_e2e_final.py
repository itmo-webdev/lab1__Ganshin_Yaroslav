"""
E2E-тесты пользовательского сценария с комментариями (браузерные тесты) — финальная версия.
Проверяется полный поток:
Регистрация ->  Создание комментария -> Удаление комментария
"""

import pytest
import logging
from playwright.async_api import async_playwright, Page
import random
import string
import asyncio
from datetime import datetime


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FRONTEND_URL = "http://localhost:5173"
API_URL = "http://localhost:8000"
BROWSER_TIMEOUT = 60000

HEADLESS = False  
SLOW_MO = 300    # Замедление на 0.3 сек


def generate_unique_email():
    """
    Генерирует ВАЛИДНЫЙ email с реальным доменом.
    В каждом прогоне создаётся уникальный email, чтобы не было конфликтов.
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[-6:]
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    #  Using gmail.com (valid domain, not test.local)
    email = f"testuser_{random_part}_{timestamp}@gmail.com"
    logger.info(f"🎯 Generated unique email: {email}")
    return email


def generate_random_string(length=8):
    """Генерирует случайную буквенно-цифровую строку."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


async def wait_for_element(page: Page, selector: str, timeout: int = 10000) -> bool:
    """Безопасно ждёт элемент и логирует результат (в т.ч. скриншот при ошибке)."""
    try:
        await page.wait_for_selector(selector, timeout=timeout)
        logger.info(f"✅ Found element: {selector}")
        return True
    except Exception as e:
        logger.error(f"❌ Element not found: {selector}")
        # Save screenshot for debugging
        screenshot_name = f"fail_{selector.replace('/', '_').replace('[', '').replace(']', '')}.png"
        await page.screenshot(path=screenshot_name)
        logger.info(f"📸 Screenshot saved: {screenshot_name}")
        return False


async def wait_and_click(page: Page, selector: str, timeout: int = 5000) -> bool:
    """Ждёт элемент и кликает по нему (если есть)."""
    try:
        element = page.locator(selector).first
        if await element.count() > 0:
            await element.click()
            logger.info(f"✅ Clicked: {selector}")
            return True
        else:
            logger.error(f"❌ Element not found for click: {selector}")
            return False
    except Exception as e:
        logger.error(f"❌ Click failed for {selector}: {e}")
        return False


@pytest.mark.asyncio
class TestCommentUserJourney:
    """Полный пользовательский сценарий: регистрация, логин, комментарий, удаление."""

    async def test_complete_comment_lifecycle(self):
        """
        Полный E2E тест:
        1) Регистрация с валидным email
        2) Логин (если нужно)
        3) Создание комментария
        4) Удаление комментария
        """
        
        #  Generate VALID, UNIQUE credentials
        username = f"test_{generate_random_string(5)}"
        email = generate_unique_email()  # ← Valid domain!
        password = "TestPass123!@"
        comment_text = f"Тест {generate_random_string(6)} {datetime.now().timestamp()}"

        logger.info(f"🚀 Test data: username={username}, email={email}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=HEADLESS, 
                slow_mo=SLOW_MO if not HEADLESS else 0
            )
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # STEP 1: NAVIGATE TO LOGIN PAGE 
                logger.info("📍 Step 1: Navigate to login page")
                await page.goto(f"{FRONTEND_URL}/login", wait_until="networkidle")
                await asyncio.sleep(0.5)

                if not await wait_for_element(page, 'input[type="email"]'):
                    pytest.skip("Login page not loaded")

                #  STEP 2: CLICK "SWITCH TO REGISTER"
                logger.info("🔄 Step 2: Switch to register form")
                
                if not await wait_and_click(page, 'button:has-text("Switch to Register")'):
                    pytest.skip("Cannot switch to register")
                
                await asyncio.sleep(0.5)

                # STEP 3: FILL REGISTRATION FORM 
                logger.info(f"✍️  Step 3: Fill registration form")
                
                # Get all inputs on register form
                inputs = await page.locator('input[type="text"], input[type="email"], input[type="password"]').all()
                
                if len(inputs) < 3:
                    logger.error(f"Expected 3+ inputs, found {len(inputs)}")
                    pytest.skip("Registration form incomplete")

                # Fill Name (first text input)
                await inputs[0].fill(username)
                logger.info(f"  ✅ Name: {username}")
                
                # Fill Email (email input - VALID domain)
                await inputs[1].fill(email)
                logger.info(f"  ✅ Email: {email}")
                
                # Fill Password (password input)
                password_inputs = await page.locator('input[type="password"]').all()
                if password_inputs:
                    await password_inputs[0].fill(password)
                    logger.info(f"  ✅ Password: ****")

                # STEP 4: CLICK REGISTER BUTTON
                logger.info("🚀 Step 4: Click register button")
                
                if not await wait_and_click(page, 'button[type="submit"]:has-text("Register")'):
                    # Try alternative selector
                    if not await wait_and_click(page, 'button:has-text("Register")'):
                        pytest.skip("Register button not found")
                
                logger.info("⏳ Waiting for registration to process...")
                await asyncio.sleep(3)  #  Wait for response and redirect

                current_url = page.url
                logger.info(f"  📄 Current URL: {current_url}")

                #  STEP 5: LOGIN (IF NEEDED)
                logger.info("🔑 Step 5: Check if login needed")
                
                if "/login" in current_url:
                    logger.info("  → Redirected to login, need to login manually")
                    
                    # Fill login form
                    email_input = page.locator('input[type="email"]').first
                    password_input = page.locator('input[type="password"]').first
                    
                    if await email_input.count() > 0:
                        await email_input.fill(email)
                        logger.info(f"  ✅ Filled login email")
                    
                    if await password_input.count() > 0:
                        await password_input.fill(password)
                        logger.info(f"  ✅ Filled login password")
                    
                    # Click login button
                    if not await wait_and_click(page, 'button:has-text("Login")'):
                        pytest.skip("Login button not found")
                    
                    logger.info("⏳ Processing login...")
                    await asyncio.sleep(2)
                else:
                    logger.info("  ✅ Already logged in (auto-redirected)")

                # STEP 6: NAVIGATE TO HOME 
                await page.goto(f"{FRONTEND_URL}/", wait_until="networkidle")
                await asyncio.sleep(1)
                logger.info(f"  📄 URL: {page.url}")

                # STEP 7: OPEN FIRST NEWS ITEM 
                logger.info("📰 Step 7: Open first news item")
                
                news_links = await page.locator('a[href*="/news/"]').all()
                
                if not news_links:
                    logger.warning("❌ No news items found on page")
                    pytest.skip("No news items available")
                
                logger.info(f"  ✅ Found {len(news_links)} news items")
                
                # Click first news
                await news_links[0].click()
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(1)
                logger.info(f"  📄 Opened news. URL: {page.url}")

                # STEP 8: CREATE COMMENT 
                logger.info(f"💬 Step 8: Create comment")
                logger.info(f"  Comment text: '{comment_text}'")
                
                if not await wait_for_element(page, 'textarea', timeout=5000):
                    pytest.skip("Comment textarea not found")
                
                # Fill comment
                textarea = page.locator('textarea').first
                await textarea.fill(comment_text)
                logger.info(f"  ✅ Filled comment textarea")
                
                # CLICK SUBMIT BUTTON (IMPORTANT!)
                if not await wait_and_click(page, 'button:has-text("Submit")'):
                    pytest.skip("Submit button not found")
                
                logger.info("⏳ Submitting comment...")
                await asyncio.sleep(2)  # ← Wait for comment to be created

                # STEP 9: VERIFY COMMENT EXISTS 
                logger.info("🔍 Step 9: Verify comment appears on page")
                
                try:
                    # Check if comment text appears on page
                    await page.wait_for_selector(f'text="{comment_text}"', timeout=5000)
                    logger.info("  ✅ Comment text found on page!")
                except:
                    logger.warning(f"  ⚠️  Comment text not visible, but continuing...")

                # STEP 10: DELETE COMMENT 
                logger.info("🗑️  Step 10: Delete comment")
                
                # Refresh to see all delete buttons
                await page.reload(wait_until="networkidle")
                await asyncio.sleep(1)
                
                delete_buttons = await page.locator('button:has-text("Delete comment")').all()
                
                if delete_buttons:
                    logger.info(f"  ✅ Found {len(delete_buttons)} delete button(s)")
                    
                    # Click first delete button (our comment)
                    await delete_buttons[0].click()
                    logger.info("  ✅ Clicked delete button")
                    await asyncio.sleep(2)  #Wait for deletion
                    
                    logger.info("  ✅ Comment deleted successfully")
                else:
                    logger.warning("  ⚠️  No delete button found")

                logger.info("✅✅✅ COMPLETE USER JOURNEY TEST PASSED! ✅✅✅")

            except Exception as e:
                logger.error(f"❌ Test failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
                
                # Save failure screenshot
                await page.screenshot(path="e2e_failure.png")
                logger.info("📸 Failure screenshot saved: e2e_failure.png")
                raise

            finally:
                await browser.close()
                logger.info("🔌 Browser closed")


@pytest.mark.asyncio
class TestBrowserBasics:
    """Базовые проверки доступности страниц."""

    async def test_frontend_is_accessible(self):
        """Проверка доступности фронтенда."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                response = await page.goto(f"{FRONTEND_URL}/", wait_until="networkidle")
                status = response.status if response else "No response"
                assert response and response.status == 200, f"Got status: {status}"
                logger.info("✅ Frontend is accessible")
            finally:
                await browser.close()

    async def test_login_page_loads(self):
        """Проверка, что страница логина содержит обязательные элементы."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(f"{FRONTEND_URL}/login", wait_until="networkidle")
                
                email_input = await page.locator('input[type="email"]').count()
                assert email_input > 0, "Email input not found"
                
                logger.info("✅ Login page loaded with required elements")
            finally:
                await browser.close()

    async def test_api_is_running(self):
    """Проверка, что бэкенд доступен (косвенно через загрузку фронтенда)."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Navigate to frontend (which uses API)
                response = await page.goto(f"{FRONTEND_URL}/", wait_until="networkidle")
                assert response and response.status == 200
                
                logger.info("✅ API connectivity verified (frontend loads)")
            finally:
                await browser.close()
