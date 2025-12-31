import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import fitz  # هذه هي مكتبة PyMuPDF القوية

TOKEN = os.getenv("TELEGRAM_TOKEN")

# ==========================================
# 🕵️ قائمة النصوص المطلوب إخفاؤها
# ==========================================
# اكتب هنا أي رقم أو كلمة تبغى البوت يغطيها
# ملاحظة: الأرقام والإنجليزي دقتها 100%، العربي أحياناً يحتاج تجربة
TEXT_TO_HIDE = [
    "Torod Customer",       # مثال: رقم الحساب في بوليصتك
    "Order shipped with Torod"
]
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("هلا! 🕵️\nأرسل ملف PDF وراح أبحث عن الكلمات المحددة وأغطيها بمربع أبيض تلقائياً.")

def redact_text_from_pdf(input_bytes):
    # فتح الملف من الذاكرة
    doc = fitz.open(stream=input_bytes, filetype="pdf")
    
    # نلف على كل صفحة
    for page in doc:
        for text in TEXT_TO_HIDE:
            # 1. البحث عن النص (يرجع لنا إحداثيات الكلمة)
            areas = page.search_for(text)
            
            # 2. وضع مربع أبيض فوق كل مكان وجدنا فيه الكلمة
            for area in areas:
                # إنشاء أمر الطمس (Redaction)
                page.add_redact_annot(area, fill=(1, 1, 1)) # (1,1,1) يعني لون أبيض
            
            # 3. تنفيذ الطمس فعلياً
            page.apply_redactions()

    # حفظ الملف المعدل
    output_bytes = doc.write()
    return output_bytes

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document
    if not file.mime_type == 'application/pdf':
        await update.message.reply_text("أرسل ملف PDF فقط.")
        return

    msg = await update.message.reply_text("جاري البحث والطمس... 🕵️‍♂️")
    
    try:
        # تحميل الملف
        file_obj = await file.get_file()
        file_data = await file_obj.download_as_bytearray()
        
        # المعالجة
        edited_pdf_bytes = redact_text_from_pdf(file_data)
        
        # الإرسال
        await update.message.reply_document(
            document=edited_pdf_bytes,
            filename=f"Redacted_{file.file_name}",
            caption="تم طمس البيانات المحددة ✅"
        )
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg.message_id)

    except Exception as e:
        await update.message.reply_text(f"حدث خطأ: {e}")

def main():
    if not TOKEN: return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.run_polling()

if __name__ == "__main__":
    main()
