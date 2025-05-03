from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List
import json
from weasyprint import HTML
import smtplib
from email.message import EmailMessage
import os
from datetime import datetime
from pathlib import Path

# === Spacy Setup ===
import spacy
from spacy.util import is_package

model_name = "en_core_web_sm"

if not is_package(model_name):
    from spacy.cli import download
    download(model_name)

nlp = spacy.load(model_name)

# === FastAPI Setup ===
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory=".")

# Load product data
with open("static/product.json", "r") as f:
    PRODUCTS = json.load(f)

# Models
class OrderItem(BaseModel):
    product: str
    quantity: int

class Order(BaseModel):
    name: str
    email: str
    items: List[OrderItem]

# Routes
@app.get("/", response_class=HTMLResponse)
async def serve_form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "products": PRODUCTS})

@app.post("/submit")
async def submit_order(
    name: str = Form(...),
    email: str = Form(...),
    products: str = Form(...)
):
    try:
        items = json.loads(products)
    except json.JSONDecodeError:
        return {"status": "error", "message": "Invalid products JSON"}

    # NLP example (optional)
    doc = nlp(name)
    print("Name tokens:", [(token.text, token.pos_) for token in doc])

    # Generate HTML for PDF
    html_content = f"""
    <h1>Order from {name}</h1>
    <p>Email: {email}</p>
    <table border="1" cellpadding="5" cellspacing="0">
        <tr><th>Product</th><th>Quantity</th></tr>
        {''.join(f'<tr><td>{item["product"]}</td><td>{item["quantity"]}</td></tr>' for item in items)}
    </table>
    """
    pdf_filename = f"order_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    HTML(string=html_content).write_pdf(pdf_filename)

    # Email settings
    HEAD_OFFICE_EMAIL = os.getenv("HEAD_OFFICE_EMAIL", "example@example.com")
    EMAIL_SENDER = os.getenv("EMAIL_SENDER", "example@example.com")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "password")  # Set securely

    # Send email
    msg = EmailMessage()
    msg["Subject"] = f"New Order from {name}"
    msg["From"] = EMAIL_SENDER
    msg["To"] = HEAD_OFFICE_EMAIL
    msg.set_content(f"Attached is a new order from {name} ({email}).")

    with open(pdf_filename, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=pdf_filename)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        return {"status": "error", "message": f"Email failed: {str(e)}"}

    # Clean up PDF
    Path(pdf_filename).unlink(missing_ok=True)

    return {"status": "success", "message": "Order submitted"}

# Required for Render or GitHub deploy
if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
