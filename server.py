from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import smtplib
from email.message import EmailMessage
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
from pydantic import BaseModel
from typing import List

app = FastAPI()

# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup template paths
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
env = Environment(loader=FileSystemLoader("templates"))

# Load product list
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    with open("static/product.json", "r") as f:
        product_data = json.load(f)
    return templates.TemplateResponse("index.html", {"request": request, "products": product_data})

# Pydantic models for safety
class ProductItem(BaseModel):
    material: str
    product: str
    thickness: str
    Grade: str
    Size: str
    Side: str
    topshade: str
    shadeName: str
    texture: str
    productCertification: str
    qualityMark: str
    boards: int
    weight: float
    totalWeight: float
    remarks: str

class OrderData(BaseModel):
    billing: str
    shipping: str
    po: str
    orderDate: str
    mobile: str
    contact: str
    executive: str
    remarks: str
    items: List[ProductItem]
    totalBoards: int
    totalWeight: float

@app.post("/submit-order")
async def submit_form(request: Request):
    try:
        data = await request.json()
        template = env.get_template("pdf_template.html")

        # Render HTML from template
        html_out = template.render(
            billing=data["billing"],
            shipping=data["shipping"],
            po=data["po"],
            orderDate=data["orderDate"],
            mobile=data["mobile"],
            contact=data["contact"],
            executive=data["executive"],
            remarks=data["remarks"],
            items=data["items"],
            totalBoards=data["totalBoards"],
            totalWeight=data["totalWeight"]
        )

        # Generate PDF
        pdf_path = f"/tmp/order_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        HTML(string=html_out).write_pdf(pdf_path)

        # Email PDF
        msg = EmailMessage()
        msg["Subject"] = "New Customer Order"
        msg["From"] = os.environ.get("EMAIL_SENDER")
        msg["To"] = os.environ.get("EMAIL_RECEIVER")
        msg.set_content("New order received. PDF attached.")

        with open(pdf_path, "rb") as f:
            msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename="CustomerOrder.pdf")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(os.environ.get("EMAIL_SENDER"), os.environ.get("EMAIL_PASSWORD"))
            smtp.send_message(msg)

        return JSONResponse(status_code=200, content={"status": "success", "message": "Order submitted and email sent."})

    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Email failed: {str(e)}"})


# Required for Render or GitHub deploy
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
