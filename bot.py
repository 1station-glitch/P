import os
import io
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# التوكين من متغيرات البيئة (نفس طريقة GitHub Actions السابقة)
TOKEN = os.getenv("TELEGRAM_TOKEN")

# ==========================================
# ⚙️ منطقة إعدادات المربعات البيضاء
# ==========================================
# الإحداثيات: (x: من اليسار, y: من الأسفل, width: العرض, height: الارتفاع)

BOXES_CONFIG = [
    # 1. المربع الأول: تغطية اسم المرسل (تحت رقم الحساب)
    (30, 485, 200, 25),

    # 2. المربع الثاني: تغطية الملاحظات (فوق وصف الشحنة)
    (30, 140, 350, 35),

    # 3. المربع الثالث: تغطية الشريط السفلي الأزرق بالكامل
    (0, 0, 600, 80),
]
# ==========================================


# دالة الترحيب
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً! 🤖\nأنا مبرمج على وضع مربعات بيضاء في أماكن محددة.\nأرسل أي ملف PDF وسأقوم بتعديله فوراً.")

# --- دالة مساعدة 1: إنشاء صفحة "الختم" التي تحتوي على المربعات البيضاء ---
def create_white_boxes_layer():
    packet = io.BytesIO()
    # إنشاء كانفاس (لوحة رسم)
    can = canvas.Canvas(packet)
    
    # إعداد لون التعبئة (أبيض)
    can.setFillColorRGB(1, 1, 1) # (Red=1, Green=1, Blue=1) = White
    
    # رسم المربعات بناءً على الإعدادات اللي فوق
    for (x, y, width, height) in BOXES_CONFIG:
        # fill=1 يعني لونه من الداخل، stroke=0 يعني بدون حدود خارجية
        can.rect(x, y, width, height, fill=1, stroke=0)
        
    can.save()
    packet.seek(0)
    return packet

# --- دالة مساعدة 2: عملية الدمج ---
def apply_boxes_to_pdf(input_stream):
    # 1. نجهز طبقة المربعات البيضاء
    stamp_layer_io = create_white_boxes_layer()
    stamp_pdf = PdfReader(stamp_layer_io)
    stamp_page = stamp_pdf.pages[0]

    # 2. نقرأ الملف الأصلي
    reader = PdfReader(input_stream)
    writer = PdfWriter()

    # 3. نلف على كل صفحة في الملف الأصلي وندمج الطبقة فوقها
    for page in reader.pages:
        # هذا الأمر يدمج صفحة المربعات فوق الصفحة الحالية
        page.merge_page(stamp_page, over=True)
        writer.add_page(page)

    # 4. حفظ النتيجة في الذاكرة
    output_stream = io.BytesIO()
    writer.write(output_stream)
    output_stream.seek(0)
    return output_stream


# --- المعالج الرئيسي لاستقبال الملفات ---
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document
    # التأكد أنه PDF
    if not file.mime_type == 'application/pdf':
        await update.message.reply_text("يرجى إرسال ملف PDF فقط.")
        return

    status_msg = await update.message.reply_text("جاري وضع المربعات البيضاء... ⬜⚙️")
    
    # تحميل الملف للذاكرة
    file_obj = await file.get_file()
    file_data = await file_obj.download_as_bytearray()
    input_stream = io.BytesIO(file_data)

    try:
        # تنفيذ التعديل
        output_pdf = apply_boxes_to_pdf(input_stream)
        
        # إرسال الملف المعدل
        await update.message.reply_document(
            document=output_pdf,
            filename=f"Edited_{file.file_name}",
            caption="تم التعديل حسب الإعدادات المسبقة ✅"
        )
        # حذف رسالة "جاري المعالجة"
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=status_msg.message_id)
        
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ أثناء المعالجة: {e}")

# --- تشغيل البوت ---
def main():
    if not TOKEN:
        print("Error: Telegram Token not found in environment variables.")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    # استقبال أي ملف وتطبيق التعديل عليه مباشرة
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    print("Bot is running in auto-edit mode...")
    app.run_polling()

if __name__ == "__main__":
    main()
