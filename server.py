from flask import Flask, request, send_from_directory, render_template
from fpdf import FPDF
import smtplib
from email.message import EmailMessage
import tempfile
import os
import json

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def home():
    return render_template('index.html')  # Serve your HTML page


@app.route('/submit-order', methods=['POST'])
def submit_order():
    # ✅ This part remains as-is (PDF generation + email)
    data = request.get_json()

    customer = data.get("billing")
    shipping = data.get("shipping")
    po = data.get("po")
    order_date = data.get("orderDate")
    mobile = data.get("mobile")
    contact = data.get("contact")
    executive = data.get("executive")
    remarks = data.get("remarks")
    items = data.get("items", [])

    # Generate PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Order Summary", ln=True, align="C")
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt=f"PO No/Date: {po} | Order Date: {order_date}", ln=True)
    pdf.cell(200, 10, txt=f"Billing: {customer}", ln=True)
    pdf.cell(200, 10, txt=f"Shipping: {shipping}", ln=True)
    pdf.cell(200, 10, txt=f"Contact: {contact} | Mobile: {mobile}", ln=True)
    pdf.cell(200, 10, txt=f"Executive: {executive}", ln=True)
    pdf.multi_cell(200, 10, txt=f"Remarks: {remarks}")
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 10)
    pdf.cell(10, 10, "Sr", 1)
    pdf.cell(30, 10, "Material", 1)
    pdf.cell(25, 10, "Product", 1)
    pdf.cell(20, 10, "Thick", 1)
    pdf.cell(15, 10, "Grade", 1)
    pdf.cell(20, 10, "Size", 1)
    pdf.cell(20, 10, "Boards", 1)
    pdf.cell(20, 10, "Weight", 1)
    pdf.cell(30, 10, "Total Wt", 1)
    pdf.ln()

    pdf.set_font("Arial", '', 10)
    for i, item in enumerate(items, 1):
        pdf.cell(10, 10, str(i), 1)
        pdf.cell(30, 10, item.get("material", "")[:15], 1)
        pdf.cell(25, 10, item.get("product", "")[:10], 1)
        pdf.cell(20, 10, item.get("thickness", ""), 1)
        pdf.cell(15, 10, item.get("grade", ""), 1)
        pdf.cell(20, 10, item.get("size", ""), 1)
        pdf.cell(20, 10, item.get("boards", ""), 1)
        pdf.cell(20, 10, item.get("weight", ""), 1)
        pdf.cell(30, 10, item.get("totalWeight", ""), 1)
        pdf.ln()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        pdf_path = tmp.name

    # Send email securely using environment variables
    smtp_user = os.environ.get("EMAIL_USER")
    smtp_pass = os.environ.get("EMAIL_PASS")

    msg = EmailMessage()
    msg["Subject"] = "New Order Received"
    msg["From"] = smtp_user
    msg["To"] = "da1@actiontesa.com"
    msg.set_content("A new order has been submitted. Please find the PDF attached.")

    with open(pdf_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename="Order.pdf")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(smtp_user, smtp_pass)
        smtp.send_message(msg)

    os.remove(pdf_path)
    return "✅ Order submitted and emailed to head office."

# Required for Render
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
