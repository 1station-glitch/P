import os
import io
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import red, black, blue

TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً! 📏\nأرسل ملف PDF وسأقوم برسم شبكة دقيقة (كل 20 نقطة) لتحديد الإحداثيات.")

def create_dense_grid_layer(width, height):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(width, height))
    
    can.setLineWidth(0.3) # خط نحيف جداً
    can.setFont("Helvetica", 6) # خط صغير للأرقام
    
    # === رسم الخطوط العمودية (X) ===
    # نمشي كل 20 خطوة عشان يعطيك دقة عالية
    for x in range(0, int(width), 20):
        if x % 100 == 0: # كل 100 نقطة نغير اللون عشان تميز
            can.setStrokeColor(red)
            can.setLineWidth(0.8)
        else:
            can.setStrokeColor(black)
            can.setLineWidth(0.3)
            
        can.line(x, 0, x, height)
        # نكتب الرقم تحت وفي النص وفوق
        can.drawString(x+1, 5, str(x))
        can.drawString(x+1, height/2, str(x))
        can.drawString(x+1, height-10, str(x))

    # === رسم الخطوط الأفقية (Y) ===
    # تذكر: الصفر يبدأ من تحت
    for y in range(0, int(height), 20):
        if y % 100 == 0: # تمييز المئات بلون أزرق
            can.setStrokeColor(blue)
            can.setLineWidth(0.8)
        else:
            can.setStrokeColor(black)
            can.setLineWidth(0.3)

        can.line(0, y, width, y)
        # نكتب الرقم يسار وفي النص ويمين
        can.drawString(1, y+1, str(y))
        can.drawString(width/2, y+1, str(y))
        can.drawString(width-20, y+1, str(y))

    can.save()
    packet.seek(0)
    return packet

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document
    
    # رسالة انتظار
    processing_msg = await update.message.reply_text("جاري رسم الشبكة الدقيقة... 📏")
    
    file_obj = await file.get_file()
    file_data = await file_obj.download_as_bytearray()
    input_stream = io.BytesIO(file_data)
    
    reader = PdfReader(input_stream)
    writer = PdfWriter()
    
    # نطبق الشبكة على الصفحة الأولى فقط
    page = reader.pages[0]
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    
    # إنشاء الطبقة
    grid_io = create_dense_grid_layer(width, height)
    grid_pdf = PdfReader(grid_io)
    
    page.merge_page(grid_pdf.pages[0])
    writer.add_page(page)
    
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    
    await update.message.reply_document(
        document=output,
        caption=f"📏 أبعاد الصفحة: {int(width)}x{int(height)}\nالخطوط الحمراء/الزرقاء كل 100 نقطة.\nالخطوط السوداء كل 20 نقطة."
    )
    # حذف رسالة الانتظار
    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_msg.message_id)

def main():
    if not TOKEN: return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.run_polling()

if __name__ == "__main__":
    main()
