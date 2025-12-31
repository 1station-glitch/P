import os
import io
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

TOKEN = os.getenv("TELEGRAM_TOKEN")

# ==========================================
# ⚙️ إعدادات المربعات (الدقيقة جداً)
# ==========================================
# أبعاد الصورة الأصلية اللي أنت عطيتني إياها (المرجع)
REF_WIDTH = 1229
REF_HEIGHT = 2008

# الإحداثيات بناءً على صورتك بالضبط (x, y, width, height)
# ملاحظة: في عالم PDF، الصفر يبدأ من تحت
BOXES_CONFIG = [
    # 1. المربع الأزرق الأول (تحت رقم الحساب)
    # الموقع: تقريباً فوق النص بشوي
    (35, 1260, 350, 60),

    # 2. المربع الأزرق الثاني (عند الملاحظات Remarks)
    # الموقع: أسفل الصفحة فوق الشريط الأزرق
    (190, 290, 900, 60),

    # 3. الشريط السفلي الأزرق كامل (Footer)
    (0, 0, 1229, 250),
]
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("هلا! 📐\nأرسل البوليصة وأنا بضبط المربعات على مقاسها بالضبط مهما كان حجمها.")

def apply_boxes_to_pdf(input_stream):
    reader = PdfReader(input_stream)
    writer = PdfWriter()

    # نلف على كل صفحة
    for page in reader.pages:
        # 1. نجيب مقاس الصفحة الحقيقي للبوليصة المرسلة
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)

        # 2. نحسب نسبة التكبير/التصغير بناءً على أبعادك (1229x2008)
        scale_x = page_width / REF_WIDTH
        scale_y = page_height / REF_HEIGHT

        # 3. ننشئ طبقة المربعات بالمقاس الجديد
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(page_width, page_height))
        can.setFillColorRGB(1, 1, 1) # لون أبيض

        for (x, y, w, h) in BOXES_CONFIG:
            # المعادلة السحرية: نضرب الإحداثيات في نسبة التحجيم
            new_x = x * scale_x
            new_y = y * scale_y
            new_w = w * scale_x
            new_h = h * scale_y
            
            can.rect(new_x, new_y, new_w, new_h, fill=1, stroke=0)

        can.save()
        packet.seek(0)
        
        # 4. دمج الطبقات
        stamp_pdf = PdfReader(packet)
        stamp_page = stamp_pdf.pages[0]
        
        # دمج ذكي
        page.merge_page(stamp_page)
        writer.add_page(page)

    output_stream = io.BytesIO()
    writer.write(output_stream)
    output_stream.seek(0)
    return output_stream

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document
    if not file.mime_type == 'application/pdf':
        await update.message.reply_text("أرسل ملف PDF يا غالي.")
        return

    msg = await update.message.reply_text("جاري القياس والرسم... 📐⬜")
    
    file_obj = await file.get_file()
    file_data = await file_obj.download_as_bytearray()
    input_stream = io.BytesIO(file_data)

    try:
        output_pdf = apply_boxes_to_pdf(input_stream)
        await update.message.reply_document(
            document=output_pdf,
            filename=f"Edited_{file.file_name}",
            caption="تم التعديل بناءً على مقاساتك 2008x1229 ✅"
        )
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg.message_id)
    except Exception as e:
        await update.message.reply_text(f"خطأ: {e}")

def main():
    if not TOKEN: return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.run_polling()

if __name__ == "__main__":
    main()
