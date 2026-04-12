"""Script to generate the sample marriage certificate PDF for testing."""
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
import os

output_path = os.path.join(os.path.dirname(__file__), "marriage_certificate.pdf")
c = canvas.Canvas(output_path, pagesize=A4)
w, h = A4

# Header banner
c.setFillColor(colors.HexColor("#1a3c6e"))
c.rect(0, h - 100, w, 100, fill=True, stroke=False)
c.setFillColor(colors.white)
c.setFont("Helvetica-Bold", 22)
c.drawCentredString(w / 2, h - 50, "CERTIFICATE OF MARRIAGE")
c.setFont("Helvetica", 12)
c.drawCentredString(w / 2, h - 72, "Office of the Registrar General, Mumbai")

c.setFillColor(colors.black)
y = h - 140

rows = [
    ("Certificate Number:", "MC/MH/2024/07/004892"),
    ("Date of Issue:", "14th July 2024"),
    ("Registrar Office:", "Bandra Sub-Registrar Office, Mumbai"),
    ("", ""),
    ("This is to certify that a marriage was solemnized between:", None),
    ("", ""),
    ("Bride (Name before Marriage):", "Priya Sharma"),
    ("Bride Date of Birth:", "15th March 1990"),
    ("Bride Father Name:", "Ramesh Sharma"),
    ("", ""),
    ("Groom (Name):", "Arjun Mehta"),
    ("Groom Date of Birth:", "22nd August 1988"),
    ("", ""),
    ("Date of Marriage:", "10th July 2024"),
    ("Place of Marriage:", "Taj Lands End, Bandra, Mumbai, MH 400050"),
    ("", ""),
    ("Name of Bride after Marriage:", "Priya Mehta"),
    ("", ""),
]

for label, value in rows:
    if label == "":
        y -= 14
        continue
    if value is None:
        c.setFont("Helvetica-Oblique", 11)
        c.drawString(72, y, label)
    else:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, y, label)
        c.setFont("Helvetica", 11)
        c.drawString(260, y, value)
    y -= 22

# Footer
c.line(72, 140, w - 72, 140)
c.setFont("Helvetica", 9)
c.drawString(72, 120, "Registrar Signature: _______________________")
c.drawString(w - 220, 120, "Seal & Date: _____________")
c.setFont("Helvetica-Oblique", 8)
c.drawCentredString(w / 2, 80, "This certificate is issued under the Special Marriage Act, 1954.")
c.drawCentredString(w / 2, 65, "Document Ref: REPO-FN-MH-2024-004892 | Verified by: Govt of Maharashtra")
c.save()
print(f"PDF created: {output_path}")
