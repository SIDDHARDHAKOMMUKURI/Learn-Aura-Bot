import os
import logging
import mimetypes
from dotenv import load_dotenv

from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from flask import Flask
import threading

app_flask = Flask(__name__)

@app_flask.route('/')
def keep_alive():
    return "LearnauraBot is running!", 200

def run_ping_server():
    app_flask.run(host="0.0.0.0", port=8080)


import google.generativeai as genai
import requests
from PyPDF2 import PdfReader
from fpdf import FPDF
from pdf2docx import Converter
import pypandoc
from pptx import Presentation

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# Logging setup
logging.basicConfig(level=logging.INFO)

# Gemini AI setup
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Handle /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to LearnauraBot!\n"
        "💬 Ask questions\n"
        "📄 Send files to auto-convert (PDF, DOCX, TXT, PPTX)\n"
        "🔍 Use /search <query> to find info online"
    )

# Gemini chatbot
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    try:
        response = model.generate_content(user_input)
        reply = response.text.strip()
    except Exception as e:
        reply = f"⚠️ Gemini Error: {e}"
    await update.message.reply_text(reply)

# SerpAPI web search
def google_search(query: str) -> str:
    url = f"https://serpapi.com/search.json?q={query}&api_key={SERPAPI_KEY}"
    try:
        res = requests.get(url)
        results = res.json().get("organic_results", [])
        if not results:
            return "No results found."
        reply = "🔍 Top Search Results:\n"
        for result in results[:3]:
            reply += f"🔗 {result.get('title')}\n{result.get('link')}\n\n"
        return reply
    except Exception as e:
        return f"⚠️ SerpAPI Error: {e}"

async def web_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Usage: /search your-query")
        return
    result = google_search(query)
    await update.message.reply_text(result)

# Smart file converter
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    filename = update.message.document.file_name
    mime_type, _ = mimetypes.guess_type(filename)

    downloaded_path = await file.download_to_drive()
    base_name, ext = os.path.splitext(filename)
    ext = ext.lower()

    converted_path = None
    reply = ""

    try:
        if ext == ".pdf":
            # PDF ➡️ Word
            converted_path = f"{base_name}_converted.docx"
            cv = Converter(downloaded_path.name)
            cv.convert(converted_path, start=0, end=None)
            cv.close()
            reply = "📄 Converted PDF to Word."

        elif ext == ".docx":
            # Word ➡️ PDF
            converted_path = f"{base_name}_converted.pdf"
            pypandoc.convert_file(downloaded_path.name, 'pdf', outputfile=converted_path)
            reply = "📝 Converted Word to PDF."

        elif ext == ".pptx":
            # PPTX ➡️ PDF
            converted_path = f"{base_name}_converted.pdf"
            pypandoc.convert_file(downloaded_path.name, 'pdf', outputfile=converted_path)
            reply = "📊 Converted PPT to PDF."

        elif ext == ".txt":
            # TXT ➡️ PDF
            converted_path = f"{base_name}_converted.pdf"
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            with open(downloaded_path.name, 'r', encoding='utf-8') as f:
                for line in f:
                    pdf.cell(200, 10, txt=line.strip(), ln=True)
            pdf.output(converted_path)
            reply = "📜 Converted Text to PDF."

        else:
            reply = "⚠️ Unsupported file type for conversion."

        if converted_path and os.path.exists(converted_path):
            await update.message.reply_document(InputFile(converted_path), caption=reply)
        else:
            await update.message.reply_text(reply)

    except Exception as e:
        await update.message.reply_text(f"❌ Conversion failed: {e}")

# Main bot setup
if __name__ == "__main__":
    # Start the ping server
    threading.Thread(target=run_ping_server).start()

    # Start Telegram bot
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", web_search))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    print("Bot is running...")
    app.run_polling()
