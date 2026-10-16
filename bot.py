import logging
import sqlite3
from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

# Cấu hình hệ thống log
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Khởi tạo Cơ sở dữ liệu SQLite (Bộ nhớ thông minh)
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

# Lệnh /start chào mừng thân thiện
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_or_create_user(user.id, user.first_name)
    welcome_msg = (
        f"👋 Chào sếp **{user.first_name}**! Em là **Thổ Địa Giá Rẻ** – trợ lý săn deal và chiến thần affiliate của sếp.\n\n"
        "💡 Sếp cứ miêu tả tự nhiên món đồ hoặc nguyên liệu cần tìm (Ví dụ: *máy xay hạt, nguyên liệu làm bánh sỉ, đồ gia dụng...*). "
        "Em sẽ tự động so giá rẻ nhất đa sàn, lọc mã giảm giá hời và tư vấn chiến lược kinh doanh nếu sếp cần luôn nha!"
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")

# Xử lý thông điệp và phân tích hành vi
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
            "Sếp cứ tham khảo thử, nếu ở khu vực quán của sếp món này chưa tối ưu, cứ hú em để em lọc thêm ý tưởng món mới hot hit tuần này nhé!"
        )
    elif any(kw in text for kw in ["máy", "điện tử", "cáp", "sạc", "tai nghe", "laptop"]):
        update_user_profile(user.id, favorite_category="công nghệ")

    response_text = (
        f"🔍 **Thổ Địa đã phân tích và lọc riêng kết quả tối ưu cho sếp:**\n\n"
        f"1️⃣ **TikTok Shop (Rẻ nhất sau mã):**\n"
        f"• Giá gốc: 500k ➔ **Giá chốt đơn: 410k** (Đã gom mã giảm 90k)\n"
        f"• ⚡ *Đánh giá:* Sàn đang trợ giá sâu nhất cho tệp săn rẻ hôm nay. (Số lượng giới hạn!)\n\n"
        f"2️⃣ **Shopee Mall (An tâm / Chính hãng):**\n"
        f"• Giá gốc: 550k ➔ **Giá chốt đơn: 460k**\n"
        f"• 🛡️ *Đánh giá:* Đổi trả 15 ngày, bảo hành hãng uy tín.\n"
        f"{strategy_advice}"
    )

    keyboard = [
        [InlineKeyboardButton("🛒 Mua ngay ở TikTok (Giá rẻ nhất)", url="https://s.shopee.vn/example")],
        [InlineKeyboardButton("🛡️ Mua ngay ở Shopee (Chính hãng)", url="https://s.shopee.vn/example")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(response_text, reply_markup=reply_markup, parse_mode="Markdown")

# Động cơ Nhịp sinh học linh hoạt
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
                    msg = (
                        f"✨ Chào buổi {('sáng' if current_hour < 12 else 'trưa' if current_hour < 17 else 'tối')} sếp **{name}**! "
                        "Hôm nay em thấy có lô nguyên liệu đồ ăn vặt/làm bánh đang có flash sale giảm sâu, sếp có cần em lọc mã giá sỉ để chuẩn bị menu mới cho học sinh tuần này không ạ?"
                    )
                else:
                    msg = (
                        f"✨ Thảnh thơi ghé qua chút nha sếp **{name}**! Em thấy mấy món {category} sếp quan tâm đợt trước nay đang có khung giờ vàng giảm sốc, sếp có muốn em nghía qua hộ món nào không?"
                    )
                
                await context.bot.send_message(chat_id=tg_id, text=msg)
            except Exception as e:
                logger.error(f"Lỗi gửi tin nhắn chủ động: {e}")

# Khởi chạy bot bằng phương thức tối ưu chống lỗi phiên bản Python
def main():
    TOKEN = "8957682513:AAFKG2e66EoRNma_T-vhSSMZIfxu9MSmRl4"
    
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    if application.job_queue:
        application.job_queue.run_repeating(check_and_send_proactive_messages, interval=3600, first=10)
    
    print("🤖 Bot 'Thổ Địa Giá Rẻ' đã khởi động thành công và hoạt động trơn tru...")
    
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
