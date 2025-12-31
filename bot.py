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
# ⚙️ منطقة إعدادات المربعات البيضاء (المهمة)
# ==========================================
# هنا تحدد الأماكن اللي تبي تغطيها.
# الصيغة: (المسافة من اليسار x, المسافة من الأسفل y, العرض width, الارتفاع height)
# الأرقام تقريبية، لازم تجرب لين تضبط المقاس اللي تبيه.

BOXES_CONFIG = [
    # المثال الأول: مربع يغطي منطقة في أعلى اليمين (مثلاً تاريخ أو لوقو)
    (450, 750, 100, 30),
    
    # المثال الثاني: مربع يغطي منطقة في منتصف الصفحة (مثلاً الأسعار)
    (250, 400, 150, 50),

    # المثال الثالث: مربع صغير في أسفل اليسار
    (20, 20, 200, 30),
    
    # 👉 أضف أو احذف أسطر حسب حاجتك
]
# ==========================================


# دالة الترحيب
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً! 🤖\nأنا مبرمج على وضع مربعات بيضاء في أماكن محددة.\nأرسل أي ملف PDF وسأقوم بتعديله فوراً.")

# --- دالة مساعدة 1: إنشاء صفحة "الختم" التي تحتوي على المربعات البيضاء ---
# --- استبدل دالة رسم المربعات بهذه الدالة المؤقتة ---
def create_white_boxes_layer():
    packet = io.BytesIO()
    can = canvas.Canvas(packet)
    
    # 1. رسم شبكة خطوط (Grid) عشان تعرف المقاسات
    can.setStrokeColorRGB(0.7, 0.7, 0.7) # لون رمادي فاتح
    can.setFont("Helvetica", 8) # خط صغير للأرقام
    
    # رسم خطوط عمودية (X) كل 50 نقطة
    for x in range(0, 600, 50):
        can.line(x, 0, x, 850)
        can.drawString(x + 2, 10, str(x)) # يكتب الرقم تحت

    # رسم خطوط أفقية (Y) كل 50 نقطة
    for y in range(0, 900, 50):
        can.line(0, y, 600, y)
        can.drawString(5, y + 2, str(y)) # يكتب الرقم يسار

    # 2. (اختياري) رسم المربعات الحالية بلون أحمر شفاف عشان تشوف مكانها
    can.setFillColorRGB(1, 0, 0, 0.3) # أحمر شفاف
    for (x, y, w, h) in BOXES_CONFIG:
        can.rect(x, y, w, h, fill=1, stroke=1)
        
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
