from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from pydantic import BaseModel
from typing import List, Dict
import json
from weasyprint import HTML
import smtplib
from email.message import EmailMessage
import os
from datetime import datetime
from pathlib import Path
import spacy
from spacy.util import is_package

# --- Spacy Setup ---
model_name = "en_core_web_sm"
if not is_package(model_name):
    from spacy.cli import download
    download(model_name)
nlp = spacy.load(model_name)

# --- FastAPI Setup ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")  # Ensure FastAPI loads your HTML templates

# Load product data (used for serving the form, if needed)
with open("static/product.json", "r") as f:
    PRODUCTS = json.load(f)

# --- Define the Pydantic Model matching the JSON payload ---
class OrderPayload(BaseModel):
    billing: str
    shipping: str
    po: str
    orderDate: str
    mobile: str
    contact: str
    executive: str
    remarks: str
    totalBoards: str
    totalWeight: str
    items: List[Dict[str, str]]

# --- Routes ---
@app.get("/", response_class=HTMLResponse)
async def serve_form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "products": PRODUCTS})

# Updated endpoint to match the client's endpoint and payload type
@app.post("/submit-order")
async def submit_order(order: OrderPayload, request: Request):
    """ Generate PDF using the existing index.html template """
    
     # Render the HTML template dynamically with order data
    rendered_html = templates.TemplateResponse("index.html", {"request": request, "order": order}).body.decode("utf-8")
    
    pdf_filename = f"order_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    HTML(string=html_content).write_pdf(pdf_filename)

    # Email settings (ensure environment variables are set correctly)
    HEAD_OFFICE_EMAIL = os.getenv("HEAD_OFFICE_EMAIL", "example@example.com")
    EMAIL_SENDER = os.getenv("EMAIL_SENDER", "example@example.com")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "password")  # Secure this in production

    # Prepare the email
    msg = EmailMessage()
    msg["Subject"] = f"New Order from {order.billing}"
    msg["From"] = EMAIL_SENDER
    msg["To"] = HEAD_OFFICE_EMAIL
    msg.set_content(f"Attached is a new order from {order.billing} (Mobile: {order.mobile}).")

    with open(pdf_filename, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=pdf_filename)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Email failed: {str(e)}"})

    # Clean up the generated PDF file
    Path(pdf_filename).unlink(missing_ok=True)

    return {"status": "success", "message": "Order submitted"}

# Required for Render or GitHub deploy
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
