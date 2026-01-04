from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os
import importlib
import socket
import time
from datetime import datetime
from utils import LOGGER

app = FastAPI(
    title="A360",
    description="A Project Made To Centralize Various APIs 📖 No Authorization Needed, All Endpoints Included :"
)

start_time = time.time()

def load_index_html():
    try:
        with open("templates/index.html", "r") as file:
            return file.read()
    except FileNotFoundError:
        LOGGER.error("index.html not found in templates directory")
        return "<h1>Welcome to AbirAPI</h1><p>Index page not found.</p>"

def load_report_html():
    try:
        with open("templates/report.html", "r") as file:
            return file.read()
    except FileNotFoundError:
        LOGGER.error("report.html not found in templates directory")
        return "<h1>API Report</h1><p>Report page not found.</p>"

def load_health_html():
    try:
        with open("templates/health.html", "r") as file:
            return file.read()
    except FileNotFoundError:
        LOGGER.error("health.html not found in templates directory")
        return "<h1>API Health</h1><p>Health page not found.</p>"

def get_actual_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def get_server_address():
    ip = get_actual_ip()
    port = int(os.getenv("PORT", 4434))
    return f"http://{ip}:{port}"

def get_uptime():
    uptime_seconds = time.time() - start_time
    days, rem = divmod(uptime_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"

def count_plugins():
    plugins_dir = "plugins"
    return len([f for f in os.listdir(plugins_dir) if f.endswith(".py") and f != "__init__.py"])

def count_endpoints():
    return len([route for route in app.routes if route.path != "/"])

@app.get("/", response_class=HTMLResponse)
async def root():
    return load_index_html()

@app.get("/report", response_class=HTMLResponse)
async def report():
    return load_report_html()

@app.get("/health", response_class=HTMLResponse)
async def health():
    return load_health_html()

@app.get("/api/health")
async def health_api():
    return {
        "Api Owner": "@ISmartCoder",
        "Api Developer": "@ISmartCoder",
        "Api Updates": "@TheSmartDev",
        "Api About": "An Asynchronous Multifunctional API Built With Pyrofork Telethon & FastAPI Framework & Python Lang By @ISmartCoder",
        "Api Version": "1.16.1",
        "Api Health": "Operational",
        "Api Uptime": get_uptime(),
        "Total Endpoints": count_endpoints(),
        "Total Plugins": count_plugins(),
        "Last Checked": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    }

def load_plugins():
    plugins_dir = "plugins"
    for filename in os.listdir(plugins_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = filename[:-3]
            try:
                module = importlib.import_module(f"plugins.{module_name}")
                if hasattr(module, "router"):
                    app.include_router(module.router)
                    LOGGER.info(f"Successfully loaded plugin: {module_name}")
                else:
                    LOGGER.warning(f"Plugin {module_name} does not have a router")
            except Exception as e:
                LOGGER.error(f"Failed to load plugin {module_name}: {str(e)}")

load_plugins()

if __name__ == "__main__":
    import uvicorn
    host = "0.0.0.0"
    port = int(os.getenv("PORT", 4434))
    LOGGER.info(f"API Running At {get_server_address()}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("RELOAD", "false").lower() == "true"
    )