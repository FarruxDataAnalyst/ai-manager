import os
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
import google.generativeai as genai

# Tokenlarni to'g'ridan-to'g'ri yozmaymiz, serverdan o'qiymiz:
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MY_CHAT_ID = int(os.environ.get("MY_CHAT_ID", 0))

genai.configure(api_key=GEMINI_API_KEY)
ai_model = genai.GenerativeModel('gemini-1.5-flash')

# Bazani sozlash
def init_db():
    conn = sqlite3.connect('ai_assistant.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# TSUE Dars Jadvali (Siz taqdim etgan rasm ma'lumotlari asosida)
TSUE_SCHEDULE = {
    0: "📅 Dushanba darslari:\n- 13:00 - 15:50: Xalqaro statistika | Xona: 16-Z-406/318",
    1: "📅 Seshanba darslari:\n- 13:00 - 15:50: Moliya asoslari | Xona: 16-Z-406/318",
    2: "📅 Chorshanba darslari:\n- 13:00 - 15:50: Milliy hisoblar tizimi | Xona: 16-Z-318\n- 16:00 - 18:50: Moliya asoslari | Xona: 16-Z-416",
    3: "📅 Payshanba darslari:\n- 13:00 - 15:50: Xalqaro statistika | Xona: 16-Z-317\n- 16:00 - 18:50: Milliy hisoblar tizimi | Xona: 16-Z-403",
    4: "📅 Juma darslari:\n- 13:00 - 15:50: Tarmoqlar statistikasi 1 | Xona: 16-Z-412\n- 16:00 - 18:50: Davlat moliyasi statistikasi | Xona: 16-Z-417",
    5: "📅 Shanba darslari:\n- 09:30 - 12:20: Davlat moliyasi statistikasi | Xona: 16-Z-311\n- 13:00 - 15:50: Tarmoqlar statistikasi 1 | Xona: 16-Z-315",
    6: "📅 Yakshanba: Dam olish kuni!"
}

def get_today_schedule():
    return TSUE_SCHEDULE.get(datetime.now().weekday(), "Darslar yo'q.")

# AI yordamida matndan vazifani tushunish
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    prompt = f"Foydalanuvchi shunday dedi: '{user_text}'. Shundan kelib chiqib qisqa va aniq ish vazifasini (task) shakllantirib ber. Faqat vazifaning o'zini yoz."
    
    response = ai_model.generate_content(prompt)
    clean_task = response.text.strip()
    
    conn = sqlite3.connect('ai_assistant.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (task) VALUES (?)", (clean_task,))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"✅ Tushundim, vazifa qo'shildi:\n📌 {clean_task}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 AI Productivity Manager ishga tushdi! Rejalaringizni erkin matn ko'rinishida yuboring.")

# Avtomatik eslatmalar
def schedule_jobs(application):
    scheduler = BackgroundScheduler()

    def send_notification(title):
        conn = sqlite3.connect('ai_assistant.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, task FROM tasks WHERE status='pending'")
        tasks = cursor.fetchall()
        conn.close()
        
        task_list = "\n".join([f"▫️ {t[1]}" for t in tasks]) if tasks else "▫️ Bajarilmagan tasklar yo'q."
        schedule_info = get_today_schedule()
        
        full_message = f"🔔 **{title}**\n\n{schedule_info}\n\n📌 **Faol Vazifalaringiz:**\n{task_list}"
        application.bot.send_message(chat_id=MY_CHAT_ID, text=full_message)

    # Siz belgilagan qat'iy vaqtlar
    scheduler.add_job(lambda: send_notification("🌅 Xayrli tong! 07:00 - Uyg'onish vaqti."), 'cron', hour=7, minute=0)
    scheduler.add_job(lambda: send_notification("⏰ 08:45 - Ertalabki ishga tayyorgarlik!"), 'cron', hour=8, minute=45)
    scheduler.add_job(lambda: send_notification("⚠️ 11:50 - Ertalabki ish yakuni!"), 'cron', hour=11, minute=50)
    scheduler.add_job(lambda: send_notification("🎓 12:30 - Universitetga yo'lga chiqish vaqti!"), 'cron', hour=12, minute=30)
    scheduler.add_job(lambda: send_notification("💻 19:00 - Kechki ish vaqtiga o'tish!"), 'cron', hour=19, minute=0)
    scheduler.add_job(lambda: send_notification("📊 21:30 - Kunlik yakuniy tahlil (Daily Review)!"), 'cron', hour=21, minute=30)
    scheduler.add_job(lambda: send_notification("🌙 23:45 - Uyquga tayyorgarlik (00:00 da uyqu)!"), 'cron', hour=23, minute=45)

    scheduler.start()

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    schedule_jobs(app)
    app.run_polling()

if __name__ == '__main__':
    main()