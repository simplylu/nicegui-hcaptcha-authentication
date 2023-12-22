# Import necessary modules and packages
from typing import Optional

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Import NiceGUI components and other required libraries
from nicegui import Client, app, ui
from dotenv import load_dotenv
import requests
import json
import os

# In reality, passwords would be hashed
passwords = {"admin": "admin"}

# Define unrestricted page routes (pages that can be accessed without authentication)
unrestricted_page_routes = {"/login"}

# Load environment variables from a .env file
load_dotenv()

# Define authentication middleware to restrict access to NiceGUI pages
class AuthMiddleware(BaseHTTPMiddleware):
    """This middleware restricts access to all NiceGUI pages.
    
    It redirects the user to the login page if they are not authenticated.
    """

    async def dispatch(self, request: Request, call_next):
        if not app.storage.user.get("authenticated", False):
            if request.url.path in Client.page_routes.values() and request.url.path not in unrestricted_page_routes:
                # Remember where the user wanted to go
                app.storage.user["referrer_path"] = request.url.path
                return RedirectResponse("/login")
        return await call_next(request)

# Add authentication middleware to the FastAPI app
app.add_middleware(AuthMiddleware)

# Define the main page of the NiceGUI app
@ui.page(path="/", title="Login")
def main_page() -> None:
    with ui.column().classes("absolute-center items-center"):
        ui.label(f"Hello {app.storage.user['username']}!").classes("text-2xl")
        ui.button(on_click=lambda: (app.storage.user.clear(), ui.open("/login")), icon="logout").props("outline round")

# Define the login page of the NiceGUI app
@ui.page(path="/login", title="Login")
async def login(client: Client) -> Optional[RedirectResponse]:
    # Add hCaptcha scripts to the head of the HTML page
    ui.add_head_html("""
        <script src="https://js.hcaptcha.com/1/api.js" async defer></script>
        <script>get_hcaptcha_response = () => {return document.getElementsByTagName("iframe")[0].attributes.getNamedItem("data-hcaptcha-response").nodeValue;}</script>
    """)

    # Check hCaptcha response for validation
    async def check_captcha() -> bool:
        h_captcha_response = await ui.run_javascript("get_hcaptcha_response();")
        ip = client.environ['asgi.scope']['client'][0]
        payload = {
            "secret": os.getenv("HCAPTCHA_SECRETKEY"),
            "response": h_captcha_response,
            "remoteip": ip,
            "sitekey": os.getenv("HCAPTCHA_SITEKEY")
        }
        res = requests.post(url="https://api.hcaptcha.com/siteverify", data=payload)
        try:
            res = res.json()
            if res.get("success", False):
                return True
            else:
                ui.notify(f"hCaptcha Error: {','.join(res.get('error-codes', []))}")
        except Exception as e:
            print(repr(e))
            return False

    # Function to attempt login after checking credentials and hCaptcha
    async def try_login() -> None:
        if passwords.get(username.value) == password.value:
            captcha_passed = await check_captcha()
            if captcha_passed:
                app.storage.user.update({"username": username.value, "authenticated": True})
                ui.open(app.storage.user.get("referrer_path", "/"))  # Go back to where the user wanted to go
        else:
            ui.notify("Wrong username or password", color="negative")

    # If already authenticated, redirect to the main page
    if app.storage.user.get("authenticated", False):
        return RedirectResponse("/")
    
    # Create the login page UI
    with ui.card().classes("absolute-center") as login_card:
        ui.markdown("Login with _admin_:_admin_")
        username = ui.input("Username")
        password = ui.input("Password", password=True).on("keydown.enter", try_login)
        ui.element("div").classes("h-captcha").props(f'data-sitekey="{os.getenv("HCAPTCHA_SITEKEY")}" data-theme="dark"')
        ui.button("Log in", on_click=try_login)

# Run the NiceGUI app with a random storage secret and a dark theme
ui.run(storage_secret=os.urandom(128), dark=True)