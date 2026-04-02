import os
import shutil
import uuid
import smtplib
import img2pdf

from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from PIL import Image
from rembg import remove
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

app = FastAPI(title="ImageCraft")

BASE_DIR = Path(__file__).resolve().parent
print("RUNNING FROM:", BASE_DIR)

# Serve static files
app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")

MESSAGES_FILE = BASE_DIR / "contact_messages.txt"

UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
TEMP_DIR = BASE_DIR / "temp"

for folder in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR]:
    folder.mkdir(exist_ok=True)

def read_html_file(filename: str):
    file_path = BASE_DIR / filename
    if file_path.exists():
        return HTMLResponse(content=file_path.read_text(encoding="utf-8"))
    return HTMLResponse(content=f"<h1>{filename} not found</h1>", status_code=404)

def is_allowed_image(filename: str) -> bool:
    allowed = [".jpg", ".jpeg", ".png", ".webp"]
    ext = Path(filename).suffix.lower()
    return ext in allowed

def save_upload_file(upload_file: UploadFile, destination: Path):
    with open(destination, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

@app.get("/", response_class=HTMLResponse)
async def home():
    return read_html_file("index.html")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon_ico():
    return FileResponse(BASE_DIR / "favicon.ico")

@app.get("/favicon.png", include_in_schema=False)
async def favicon_png():
    return FileResponse(BASE_DIR / "favicon.png")

@app.get("/Fevicon.png", include_in_schema=False)
async def favicon_misspelled():
    return FileResponse(BASE_DIR / "favicon.png")

# =========================
# TOOL PAGES
# =========================
@app.get("/compress-page", response_class=HTMLResponse)
async def compress_page():
    return read_html_file("compress-page.html")


@app.get("/remove-bg-page", response_class=HTMLResponse)
async def remove_bg_page():
    return read_html_file("remove-bg-page.html")


@app.get("/image-to-pdf-page", response_class=HTMLResponse)
async def image_to_pdf_page():
    return read_html_file("image-to-pdf-page.html")


@app.get("/resize-page", response_class=HTMLResponse)
async def resize_page():
    return read_html_file("resize-page.html")


# =========================
# SERVE CSS
# =========================
@app.get("/style.css")
async def get_css():
    css_path = BASE_DIR / "style.css"
    if css_path.exists():
        return FileResponse(css_path, media_type="text/css")
    return JSONResponse(
        {"success": False, "message": "style.css not found"},
        status_code=404
    )


# =========================
# SERVE JS
# =========================
@app.get("/script.js")
async def get_js():
    js_path = BASE_DIR / "script.js"
    if js_path.exists():
        return FileResponse(js_path, media_type="application/javascript")
    return JSONResponse(
        {"success": False, "message": "script.js not found"},
        status_code=404
    )


# =========================
# CONTACT FORM (SAVE + EMAIL)
# =========================
@app.post("/contact")
async def contact_form(
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...)
):
    try:
        # Load from .env
        sender_email = os.getenv("EMAIL_USER")
        sender_password = os.getenv("EMAIL_PASS")
        receiver_email = os.getenv("RECEIVER_EMAIL", "convodoc@gmail.com")

        # Validate env vars
        if not sender_email or not sender_password:
            return JSONResponse({
                "success": False,
                "message": "Email configuration missing. Please set EMAIL_USER and EMAIL_PASS in .env"
            }, status_code=500)

        # Save message locally (backup)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        contact_entry = (
            f"📩 New Contact Message\n"
            f"Time: {timestamp}\n"
            f"Name: {name}\n"
            f"Email: {email}\n"
            f"Message: {message}\n"
            f"{'-' * 50}\n"
        )

        # Print in terminal / Render logs
        print(contact_entry)

        # Save in file as backup
        with open(MESSAGES_FILE, "a", encoding="utf-8") as f:
            f.write(contact_entry)

        # Create email
        subject = f"📩 New Contact Form Message from {name}"
        body = f"""
You received a new contact form message from your ImageCraft website.

Time: {timestamp}
Name: {name}
User Email: {email}

Message:
{message}
        """

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Subject"] = subject

        # IMPORTANT:
        # When you click Reply in Gmail, reply goes to the user who submitted the form
        msg["Reply-To"] = email

        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Send email via Gmail SMTP
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()

        return JSONResponse({
            "success": True,
            "message": "Your message has been sent successfully!"
        })

    except Exception as e:
        print("Contact form error:", str(e))
        return JSONResponse({
            "success": False,
            "message": "Failed to send message. Please try again later."
        }, status_code=500)


# =========================
# IMAGE COMPRESSOR
# =========================
@app.post("/compress")
async def compress_image(file: UploadFile = File(...), quality: int = Form(70)):
    try:
        if not is_allowed_image(file.filename):
            return JSONResponse(
                {"success": False, "message": "Unsupported file format."},
                status_code=400
            )

        # Clamp quality to safe range
        quality = max(10, min(95, quality))

        ext = Path(file.filename).suffix.lower()
        input_name = f"{uuid.uuid4()}{ext}"
        input_path = UPLOAD_DIR / input_name

        save_upload_file(file, input_path)

        output_name = f"compressed_{uuid.uuid4()}.jpg"
        output_path = OUTPUT_DIR / output_name

        img = Image.open(input_path).convert("RGB")
        img.save(output_path, "JPEG", optimize=True, quality=quality)

        return JSONResponse({
            "success": True,
            "download_url": f"/download/{output_name}",
            "message": "Image compressed successfully!"
        })

    except Exception as e:
        print("Compress error:", str(e))
        return JSONResponse(
            {"success": False, "message": "Failed to compress image."},
            status_code=500
        )


# =========================
# BACKGROUND REMOVER
# =========================
@app.post("/remove-bg")
async def remove_background(file: UploadFile = File(...)):
    try:
        if not is_allowed_image(file.filename):
            return JSONResponse(
                {"success": False, "message": "Unsupported file format."},
                status_code=400
            )

        ext = Path(file.filename).suffix.lower()
        input_name = f"{uuid.uuid4()}{ext}"
        input_path = UPLOAD_DIR / input_name

        save_upload_file(file, input_path)

        output_name = f"no_bg_{uuid.uuid4()}.png"
        output_path = OUTPUT_DIR / output_name

        with open(input_path, "rb") as inp:
            input_data = inp.read()

        output_data = remove(input_data)

        with open(output_path, "wb") as out:
            out.write(output_data)

        return JSONResponse({
            "success": True,
            "download_url": f"/download/{output_name}",
            "message": "Background removed successfully!"
        })

    except Exception as e:
        print("Remove BG error:", str(e))
        return JSONResponse(
            {"success": False, "message": "Failed to remove background."},
            status_code=500
        )


# =========================
# IMAGE TO PDF
# =========================
@app.post("/image-to-pdf")
async def image_to_pdf(files: list[UploadFile] = File(...)):
    try:
        image_paths = []

        for file in files:
            if not is_allowed_image(file.filename):
                return JSONResponse(
                    {"success": False, "message": f"Unsupported file: {file.filename}"},
                    status_code=400
                )

            ext = Path(file.filename).suffix.lower()
            input_name = f"{uuid.uuid4()}{ext}"
            input_path = TEMP_DIR / input_name

            save_upload_file(file, input_path)

            converted_path = TEMP_DIR / f"{uuid.uuid4()}.jpg"
            img = Image.open(input_path).convert("RGB")
            img.save(converted_path, "JPEG")

            image_paths.append(str(converted_path))

        output_name = f"images_{uuid.uuid4()}.pdf"
        output_path = OUTPUT_DIR / output_name

        with open(output_path, "wb") as f:
            f.write(img2pdf.convert(image_paths))

        return JSONResponse({
            "success": True,
            "download_url": f"/download/{output_name}",
            "message": "PDF created successfully!"
        })

    except Exception as e:
        print("Image to PDF error:", str(e))
        return JSONResponse(
            {"success": False, "message": "Failed to create PDF."},
            status_code=500
        )


# =========================
# IMAGE RESIZER
# =========================
@app.post("/resize")
async def resize_image(
    file: UploadFile = File(...),
    width: int = Form(...),
    height: int = Form(...)
):
    try:
        if not is_allowed_image(file.filename):
            return JSONResponse(
                {"success": False, "message": "Unsupported file format."},
                status_code=400
            )

        # Basic validation
        if width <= 0 or height <= 0:
            return JSONResponse(
                {"success": False, "message": "Width and height must be greater than 0."},
                status_code=400
            )

        # Prevent absurd sizes
        if width > 10000 or height > 10000:
            return JSONResponse(
                {"success": False, "message": "Width or height is too large."},
                status_code=400
            )

        ext = Path(file.filename).suffix.lower()
        input_name = f"{uuid.uuid4()}{ext}"
        input_path = UPLOAD_DIR / input_name

        save_upload_file(file, input_path)

        output_name = f"resized_{uuid.uuid4()}{ext}"
        output_path = OUTPUT_DIR / output_name

        img = Image.open(input_path)
        resized = img.resize((width, height))
        resized.save(output_path)

        return JSONResponse({
            "success": True,
            "download_url": f"/download/{output_name}",
            "message": "Image resized successfully!"
        })

    except Exception as e:
        print("Resize error:", str(e))
        return JSONResponse(
            {"success": False, "message": "Failed to resize image."},
            status_code=500
        )


# =========================
# DOWNLOAD FILE
# =========================
@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = OUTPUT_DIR / filename

    if file_path.exists():
        return FileResponse(path=file_path, filename=filename)

    return JSONResponse(
        {"success": False, "message": "File not found."},
        status_code=404
    )
    