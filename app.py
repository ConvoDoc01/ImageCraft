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
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

app = FastAPI(title="ImageCraft")

BASE_DIR = Path(__file__).resolve().parent
print("🚀 ImageCraft starting from:", BASE_DIR)

# =========================
# PATHS
# =========================
MESSAGES_FILE = BASE_DIR / "contact_messages.txt"

UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
TEMP_DIR = BASE_DIR / "temp"
STATIC_DIR = BASE_DIR / "static"

# Create required folders
for folder in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR, STATIC_DIR]:
    folder.mkdir(exist_ok=True)

# Mount static folder safely
# NOTE: Put any static assets inside /static folder if possible
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# =========================
# HELPERS
# =========================
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


# =========================
# HEALTH CHECK (IMPORTANT FOR DEBUG)
# =========================
@app.get("/health")
async def health_check():
    return {"status": "ok", "app": "ImageCraft"}


# =========================
# HOME + ROOT FILES
# =========================
@app.get("/", response_class=HTMLResponse)
async def home():
    return read_html_file("index.html")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon_ico():
    file_path = BASE_DIR / "favicon.ico"
    if file_path.exists():
        return FileResponse(file_path)
    return JSONResponse({"success": False, "message": "favicon.ico not found"}, status_code=404)


@app.get("/favicon.png", include_in_schema=False)
async def favicon_png():
    file_path = BASE_DIR / "favicon.png"
    if file_path.exists():
        return FileResponse(file_path)
    return JSONResponse({"success": False, "message": "favicon.png not found"}, status_code=404)


@app.get("/Fevicon.png", include_in_schema=False)
async def favicon_misspelled():
    file_path = BASE_DIR / "favicon.png"
    if file_path.exists():
        return FileResponse(file_path)
    return JSONResponse({"success": False, "message": "favicon.png not found"}, status_code=404)


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
# SERVE ROOT CSS / JS (for your current project structure)
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
        sender_email = os.getenv("EMAIL_USER")
        sender_password = os.getenv("EMAIL_PASS")
        receiver_email = os.getenv("RECEIVER_EMAIL", "convodoc@gmail.com")

        if not sender_email or not sender_password:
            return JSONResponse({
                "success": False,
                "message": "Email configuration missing. Please set EMAIL_USER and EMAIL_PASS."
            }, status_code=500)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        contact_entry = (
            f"📩 New Contact Message\n"
            f"Time: {timestamp}\n"
            f"Name: {name}\n"
            f"Email: {email}\n"
            f"Message: {message}\n"
            f"{'-' * 50}\n"
        )

        print(contact_entry)

        with open(MESSAGES_FILE, "a", encoding="utf-8") as f:
            f.write(contact_entry)

        subject = f"📩 New Contact Form Message from {name}"
        body = f"""You received a new contact form message from your ImageCraft website.

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
        msg["Reply-To"] = email
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())

        return JSONResponse({
            "success": True,
            "message": "Your message has been sent successfully!"
        })

    except Exception as e:
        print("❌ Contact form error:", str(e))
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
        print("❌ Compress error:", str(e))
        return JSONResponse(
            {"success": False, "message": "Failed to compress image."},
            status_code=500
        )


# =========================
# BACKGROUND REMOVER (LAZY IMPORT FIX)
# =========================
@app.post("/remove-bg")
async def remove_background(file: UploadFile = File(...)):
    input_path = None
    prepared_path = None
    output_path = None

    try:
        # Import inside route for safer debugging
        try:
            from rembg import remove
        except Exception as import_error:
            return JSONResponse(
                {
                    "success": False,
                    "message": f"rembg import failed: {str(import_error)}"
                },
                status_code=500
            )

        if not file.filename:
            return JSONResponse(
                {"success": False, "message": "No file selected."},
                status_code=400
            )

        if not is_allowed_image(file.filename):
            return JSONResponse(
                {"success": False, "message": "Unsupported file format. Use JPG, JPEG, PNG, or WEBP."},
                status_code=400
            )

        ext = Path(file.filename).suffix.lower()
        input_name = f"{uuid.uuid4()}{ext}"
        input_path = UPLOAD_DIR / input_name

        # Save upload directly to disk
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if not input_path.exists() or input_path.stat().st_size == 0:
            return JSONResponse(
                {"success": False, "message": "Uploaded file is empty."},
                status_code=400
            )

        # Prepare smaller image for rembg (important for weak hosting)
        prepared_path = TEMP_DIR / f"prepared_{uuid.uuid4()}.png"

        img = Image.open(input_path)
        img = img.convert("RGBA")

        # SUPER SAFE for live hosting
        img.thumbnail((1200, 1200))

        img.save(prepared_path, format="PNG", optimize=True)

        with open(prepared_path, "rb") as f:
            safe_bytes = f.read()

        output_name = f"no_bg_{uuid.uuid4()}.png"
        output_path = OUTPUT_DIR / output_name

        # Process
        try:
            output_data = remove(safe_bytes)
        except Exception as remove_error:
            return JSONResponse(
                {
                    "success": False,
                    "message": f"rembg processing failed: {str(remove_error)}"
                },
                status_code=500
            )

        with open(output_path, "wb") as out:
            out.write(output_data)

        return JSONResponse({
            "success": True,
            "download_url": f"/download/{output_name}",
            "message": "Background removed successfully!"
        })

    except Exception as e:
        import traceback
        print("❌ Remove BG error:", str(e))
        traceback.print_exc()

        return JSONResponse(
            {
                "success": False,
                "message": f"Background removal failed: {str(e)}"
            },
            status_code=500
        )

    finally:
        for path in [input_path, prepared_path]:
            try:
                if path and Path(path).exists():
                    Path(path).unlink()
            except Exception:
                pass

# =========================
# IMAGE TO PDF
# =========================
@app.post("/image-to-pdf")
async def image_to_pdf(files: list[UploadFile] = File(...)):
    temp_converted_files = []

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
            temp_converted_files.append(input_path)
            temp_converted_files.append(converted_path)

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
        print("❌ Image to PDF error:", str(e))
        return JSONResponse(
            {"success": False, "message": "Failed to create PDF."},
            status_code=500
        )

    finally:
        # Cleanup temp files
        for temp_file in temp_converted_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception:
                pass


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

        if width <= 0 or height <= 0:
            return JSONResponse(
                {"success": False, "message": "Width and height must be greater than 0."},
                status_code=400
            )

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
        print("❌ Resize error:", str(e))
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
