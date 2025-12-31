import os
import io
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import fitz  # مكتبة PyMuPDF

TOKEN = os.getenv("TELEGRAM_TOKEN")

# ==========================================
# 🕵️ إعدادات الطمس
# ==========================================
# 1. قائمة النصوص (أرقام، كلمات)
TEXT_TO_HIDE = [
    "Torod Customer",
    "Order shipped with Torod",
    # أضف أي نص هنا
]

# 2. إعدادات طمس الصور السفلية
# هذا الرقم يحدد "منطقة الخطر" في الأسفل.
# 0.75 تعني: أي صورة تبدأ بعد 75% من طول الصفحة (يعني في الربع الأخير تحت) سيتم طمسها.
# لو تبي ترفع المنطقة، قلل الرقم (مثلاً 0.60). لو تبي تنزلها، زوده (مثلاً 0.85).
BOTTOM_IMAGE_THRESHOLD = 0.75
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("هلا! 🕵️\nأرسل الملف وراح أطمس النصوص المحددة + أي صورة في أسفل الصفحة.")

def redact_pdf_content(input_bytes):
    doc = fitz.open(stream=input_bytes, filetype="pdf")
    
    for page in doc:
        # === أولاً: طمس النصوص المحددة ===
        for text in TEXT_TO_HIDE:
            areas = page.search_for(text)
            for area in areas:
                page.add_redact_annot(area, fill=(1, 1, 1)) # لون أبيض

        # === ثانياً: طمس الصور السفلية ===
        # 1. حساب خط العتبة (بداية منطقة الأسفل)
        # في pymupdf، الصفر يبدأ من فوق. لذا كلما زاد الرقم، نزلنا تحت.
        page_height = page.rect.height
        threshold_y = page_height * BOTTOM_IMAGE_THRESHOLD

        # 2. الحصول على قائمة بكل الصور في الصفحة
        image_list = page.get_images(full=True)

        for img_info in image_list:
            xref = img_info[0] # المعرف الفريد للصورة
            
            # 3. الحصول على المستطيل الذي يحيط بالصورة (مكانها)
            # قد ترجع أكثر من مستطيل لو الصورة مكررة
            image_rects = page.get_image_rects(xref)

            for rect in image_rects:
                # rect.y0 هو الحافة العلوية للصورة.
                # إذا كانت الحافة العلوية للصورة أكبر من خط العتبة، يعني هي تحت
                if rect.y0 > threshold_y:
                    # نغطي منطقة الصورة بمربع أبيض
                    page.add_redact_annot(rect, fill=(1, 1, 1))
                    print(f"تم طمس صورة سفلية في الموقع: {rect}")

        # تنفيذ كل عمليات الطمس دفعة واحدة
        page.apply_redactions()

    output_bytes = doc.write()
    return output_bytes

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document
    if not file.mime_type == 'application/pdf':
        await update.message.reply_text("PDF فقط لو سمحت.")
        return

    msg = await update.message.reply_text("جاري تحليل النصوص والصور وطمسها... 🕵️‍♂️⬜")
    
    try:
        file_obj = await file.get_file()
        file_data = await file_obj.download_as_bytearray()
        
        # المعالجة
        edited_pdf_bytes = redact_pdf_content(file_data)
        
        await update.message.reply_document(
            document=edited_pdf_bytes,
            filename=f"Redacted_{file.file_name}",
            caption="تم طمس النصوص المحددة + الصور السفلية ✅"
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
