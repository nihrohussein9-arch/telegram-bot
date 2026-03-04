import os
import json
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ===================== الإعدادات =====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8362490186:AAGQ7rQsCxd-7avEksnh-u9n2tlZFSzdsEk")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "1170843016"))
PDF_FOLDER = "lectures"
DATA_FILE = "lectures.json"
# ====================================================

WEEKS = [
    "الأسبوع الأول",
    "الأسبوع الثاني",
    "الأسبوع الثالث",
    "الأسبوع الرابع",
    "الأسبوع الخامس",
    "الأسبوع السادس",
    "الأسبوع السابع",
]

logging.basicConfig(level=logging.INFO)
os.makedirs(PDF_FOLDER, exist_ok=True)


def load_lectures():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_lectures(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


pending_uploads = {}


def main_keyboard():
    buttons = [[KeyboardButton("📁 " + week)] for week in WEEKS]
    buttons.append([KeyboardButton("🏠 الرجوع إلى البداية")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎓 أهلاً بك في دورة السلطان الأول!\n\n"
        "اختر الأسبوع من القائمة أدناه 👇",
        reply_markup=main_keyboard()
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🏠 الرجوع إلى البداية":
        await start(update, context)
        return

    # تحقق إذا كان النص أسبوع
    week = None
    for w in WEEKS:
        if text == "📁 " + w:
            week = w
            break

    if week:
        lectures = load_lectures()
        week_lectures = {k: v for k, v in lectures.items() if v["week"] == week}

        if not week_lectures:
            await update.message.reply_text(
                "📁 " + week + "\n\nلا توجد محاضرات في هذا الأسبوع بعد.",
                reply_markup=main_keyboard()
            )
            return

        keyboard = []
        for key, val in week_lectures.items():
            keyboard.append([InlineKeyboardButton("📄 " + val['name'], callback_data="get_" + key)])

        await update.message.reply_text(
            "📁 " + week + "\n\nاختر المحاضرة:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def send_lecture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    key = query.data.replace("get_", "")
    lectures = load_lectures()

    if key not in lectures:
        await query.message.reply_text("المحاضرة غير موجودة.")
        return

    file_path = lectures[key]["path"]
    lecture_name = lectures[key]["name"]

    await query.message.reply_text("⏳ جاري الإرسال: " + lecture_name)
    with open(file_path, "rb") as f:
        await query.message.reply_document(document=f, filename=lecture_name + ".pdf")


async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("ما عندك صلاحية.")
        return

    if not context.args or "|" not in " ".join(context.args):
        weeks_list = "\n".join(WEEKS)
        await update.message.reply_text(
            "الاستخدام:\n"
            "/upload اسم الأسبوع | اسم المحاضرة\n\n"
            "مثال:\n"
            "/upload الأسبوع الأول | مقدمة\n\n"
            "الأسابيع المتاحة:\n" + weeks_list + "\n\n"
            "ثم أرسل ملف PDF"
        )
        return

    full_text = " ".join(context.args)
    parts = full_text.split("|")
    week = parts[0].strip()
    name = parts[1].strip()

    pending_uploads[update.effective_user.id] = {"week": week, "name": name}
    await update.message.reply_text(
        "تمام! الحين أرسل ملف PDF\n\n"
        "الأسبوع: " + week + "\n"
        "الاسم: " + name
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        return

    if user_id not in pending_uploads:
        await update.message.reply_text("أرسل أولاً /upload الأسبوع | اسم المحاضرة ثم أرسل الملف.")
        return

    doc = update.message.document
    if not doc.file_name.endswith(".pdf"):
        await update.message.reply_text("الرجاء إرسال ملف PDF فقط.")
        return

    info = pending_uploads.pop(user_id)
    week = info["week"]
    name = info["name"]

    file = await doc.get_file()
    key = "lecture_" + str(len(load_lectures()) + 1)
    file_path = os.path.join(PDF_FOLDER, key + ".pdf")
    await file.download_to_drive(file_path)

    lectures = load_lectures()
    lectures[key] = {"name": name, "week": week, "path": file_path}
    save_lectures(lectures)

    await update.message.reply_text(
        "✅ تم رفع المحاضرة!\n\n"
        "الأسبوع: " + week + "\n"
        "الاسم: " + name
    )


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("ما عندك صلاحية.")
        return

    lectures = load_lectures()
    if not lectures:
        await update.message.reply_text("لا توجد محاضرات.")
        return

    keyboard = []
    for key, val in lectures.items():
        keyboard.append([InlineKeyboardButton("🗑 " + val['week'] + " - " + val['name'], callback_data="del_" + key)])

    await update.message.reply_text("اختر المحاضرة للحذف:", reply_markup=InlineKeyboardMarkup(keyboard))


async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    key = query.data.replace("del_", "")
    lectures = load_lectures()

    if key in lectures:
        name = lectures[key]["name"]
        path = lectures[key]["path"]
        if os.path.exists(path):
            os.remove(path)
        del lectures[key]
        save_lectures(lectures)
        await query.message.reply_text("✅ تم حذف: " + name)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upload", upload_command))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(send_lecture, pattern="^get_"))
    app.add_handler(CallbackQueryHandler(confirm_delete, pattern="^del_"))

    print("البوت شغال!")
    app.run_polling()


if __name__ == "__main__":
    main()
