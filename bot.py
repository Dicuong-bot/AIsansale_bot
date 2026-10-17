import logging
import sqlite3
from datetime import datetime
import pytz
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type','text/plain')
        self.end_headers()
        self.wfile.write(b"Bot Tho Dia Gia Re is running perfectly!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def init_db():
    conn = sqlite3.connect("thodia_ultimate_memory.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            name TEXT,
            shopping_style TEXT DEFAULT 'price_sensitive',
            favorite_category TEXT DEFAULT 'general',
            job_type TEXT DEFAULT 'unknown',
            preferred_hour INTEGER DEFAULT 11,
            last_interaction TIMESTAMP
        )
    """
    )
    conn.commit()
    conn.close()

init_db()

def get_or_create_user(telegram_id, name):
    conn = sqlite3.connect("thodia_ultimate_memory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute(
            """
            INSERT INTO users (telegram_id, name, shopping_style, favorite_category, job_type, preferred_hour, last_interaction)
            VALUES (?, ?, 'price_sensitive', 'general', 'unknown', 11, ?)
        """,
            (telegram_id, name, datetime.now()),
        )
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
    conn.close()
    return user

def update_user_profile(telegram_id, shopping_style=None, favorite_category=None, job_type=None, preferred_hour=None):
    conn = sqlite3.connect("thodia_ultimate_memory.db")
    cursor = conn.cursor()
    if shopping_style:
        cursor.execute("UPDATE users SET shopping_style = ? WHERE telegram_id = ?", (shopping_style, telegram_id))
    if favorite_category:
        cursor.execute("UPDATE users SET favorite_category = ? WHERE telegram_id = ?", (favorite_category, telegram_id))
    if job_type:
        cursor.execute("UPDATE users SET job_type = ? WHERE telegram_id = ?", (job_type, telegram_id))
    if preferred_hour is not None:
        cursor.execute("UPDATE users SET preferred_hour = ? WHERE telegram_id = ?", (preferred_hour, telegram_id))
    cursor.execute("UPDATE users SET last_interaction = ? WHERE telegram_id = ?", (datetime.now(), telegram_id))
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_or_create_user(user.id, user.first_name)
    welcome_msg = (
        f"👋 Chào sếp **{user.first_name}**! Em là **Thổ Địa Giá Rẻ** – trợ lý săn deal và chiến thần affiliate của sếp.\n\n"
        "💡 Sếp cứ miêu tả tự nhiên món đồ hoặc nguyên liệu cần tìm. "
        "Em sẽ tự động so giá rẻ nhất đa sàn, lọc mã giảm giá hời và tư vấn chiến lược kinh doanh nếu sếp cần luôn nha!"
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_or_create_user(user.id, user.first_name)
    text = update.message.text.lower()
    
    current_hour = datetime.now().hour
    if 7 <= current_hour <= 22:
        update_user_profile(user.id, preferred_hour=current_hour)

    strategy_advice = ""
    if any(kw in text for kw in ["bánh", "nguyên liệu", "bột", "sốt", "quán", "sỉ", "đồ ăn", "pha chế", "học sinh"]):
        update_user_profile(user.id, job_type="fb_small_business", favorite_category="thực phẩm / F&B")
        strategy_advice = (
            "\n\n💡 *Góc Thổ Địa Tư Vấn Chiến Lược Kinh Doanh:*\n"
            "Em thấy sếp đang tìm nguyên liệu phục vụ kinh doanh. Mấy món này mua sỉ trên Shopee/TikTok Shop vừa được trợ giá sâu, "
            "không cần ôm hàng tồn kho nhiều mà vẫn có giá cực tốt. "
            "Sếp cứ tham khảo thử nha!"
        )

    response_text = (
        f"🔍 **Thổ Địa đã phân tích và lọc riêng kết quả tối ưu cho sếp:**\n\n"
        f"1️⃣ **TikTok Shop (Rẻ nhất sau mã):**\n"
        f"• Giá gốc: 500k ➔ **Giá chốt đơn: 410k** (Đã gom mã giảm 90k)\n"
        f"• ⚡ *Đánh giá:* Sàn đang trợ giá sâu nhất cho tệp săn rẻ hôm nay.\n\n"
        f"2️⃣ **Shopee Mall (An tâm / Chính hãng):**\n"
        f"• Giá gốc: 550k ➔ **Giá chốt đơn: 460k**\n"
        f"{strategy_advice}"
    )

    keyboard = [
        [InlineKeyboardButton("🛒 Mua ngay ở TikTok (Giá rẻ nhất)", url="https://s.shopee.vn/example")],
        [InlineKeyboardButton("🛡️ Mua ngay ở Shopee (Chính hãng)", url="https://s.shopee.vn/example")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(response_text, reply_markup=reply_markup, parse_mode="Markdown")

async def check_and_send_proactive_messages(context: ContextTypes.DEFAULT_TYPE):
    vn_tz = pytz.timezone("Asia/Ho_Chi_Minh")
    current_time = datetime.now(vn_tz)
    current_hour = current_time.hour
    
    if current_hour < 7 or current_hour > 22:
        return

    conn = sqlite3.connect("thodia_ultimate_memory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id, name, job_type, favorite_category, preferred_hour FROM users")
    users = cursor.fetchall()
    conn.close()

    for user in users:
        tg_id, name, job_type, category, pref_hour = user
        if pref_hour == current_hour:
            try:
                if job_type == "fb_small_business":
                    msg = f"✨ Chào sếp **{name}**! Hôm nay em thấy có lô nguyên liệu đang flash sale, sếp có cần em lọc mã giá sỉ không ạ?"
                else:
                    msg = f"✨ Thảnh thơi ghé qua chút nha sếp **{name}**! Mấy món {category} sếp quan tâm đang giảm sốc đó!"
                await context.bot.send_message(chat_id=tg_id, text=msg)
            except Exception as e:
                logger.error(f"Lỗi gửi tin nhắn chủ động: {e}")

def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()

    TOKEN = "8957682513:AAFKG2e66EoRNma_T-vhSSMZIfxu9MSmRl4"
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    if application.job_queue:
        application.job_queue.run_repeating(check_and_send_proactive_messages, interval=3600, first=10)
    
    print("🤖 Bot 'Thổ Địa Giá Rẻ' đã khởi động thành công...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
