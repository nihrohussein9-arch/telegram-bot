import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ===================== الإعدادات =====================
BOT_TOKEN = "8362490186:AAGQ7rQsCxd-7avEksnh-u9n2tlZFSzdsEk"
ADMIN_ID = 1170843016
PDF_FOLDER = "lectures"
DATA_FILE = "lectures.json"
# ====================================================

logging.basicConfig(level=logging.INFO)

# إنشاء مجلد المحاضرات
os.makedirs(PDF_FOLDER, exist_ok=True)


def load_lectures():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_lectures(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# حالة الـ admin (لحفظ اسم المحاضرة مؤقتاً)
pending_uploads = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً! أنا بوت المحاضرات.\n\n"
        "📚 اضغط /lectures لعرض جميع المحاضرات المتاحة."
    )


async def lectures_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lectures = load_lectures()
    if not lectures:
        await update.message.reply_text("📭 لا توجد محاضرات متاحة حالياً.")
        return

    keyboard = []
    for key, val in lectures.items():
        keyboard.append([InlineKeyboardButton(f"📄 {val['name']}", callback_data=f"get_{key}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📚 المحاضرات المتاحة:", reply_markup=reply_markup)


async def send_lecture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    key = query.data.replace("get_", "")
    lectures = load_lectures()

    if key not in lectures:
        await query.message.reply_text("❌ المحاضرة غير موجودة.")
        return

    file_path = lectures[key]["path"]
    lecture_name = lectures[key]["name"]

    await query.message.reply_text(f"⏳ جاري إرسال: {lecture_name}")
    with open(file_path, "rb") as f:
        await query.message.reply_document(document=f, filename=f"{lecture_name}.pdf")


# ===================== أوامر الـ Admin =====================

async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ ما عندك صلاحية.")
        return

    if not context.args:
        await update.message.reply_text(
            "📝 الاستخدام:\n/upload اسم المحاضرة\n\nثم أرسل ملف الـ PDF"
        )
        return

    name = " ".join(context.args)
    pending_uploads[update.effective_user.id] = name
    await update.message.reply_text(f"✅ تمام! الحين أرسل ملف PDF للمحاضرة: *{name}*", parse_mode="Markdown")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ما عندك صلاحية لرفع ملفات.")
        return

    if user_id not in pending_uploads:
        await update.message.reply_text("⚠️ أرسل أولاً /upload اسم المحاضرة ثم أرسل الملف.")
        return

    doc = update.message.document
    if not doc.file_name.endswith(".pdf"):
        await update.message.reply_text("❌ الرجاء إرسال ملف PDF فقط.")
        return

    lecture_name = pending_uploads.pop(user_id)
    file = await doc.get_file()
    key = f"lecture_{len(load_lectures()) + 1}"
    file_path = os.path.join(PDF_FOLDER, f"{key}.pdf")

    await file.download_to_drive(file_path)

    lectures = load_lectures()
    lectures[key] = {"name": lecture_name, "path": file_path}
    save_lectures(lectures)

    await update.message.reply_text(f"✅ تم رفع المحاضرة: *{lecture_name}*", parse_mode="Markdown")


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ ما عندك صلاحية.")
        return

    lectures = load_lectures()
    if not lectures:
        await update.message.reply_text("📭 لا توجد محاضرات.")
        return

    keyboard = []
    for key, val in lectures.items():
        keyboard.append([InlineKeyboardButton(f"🗑 {val['name']}", callback_data=f"del_{key}")])

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
        await query.message.reply_text(f"🗑 تم حذف: *{name}*", parse_mode="Markdown")


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lectures", lectures_list))
    app.add_handler(CommandHandler("upload", upload_command))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(send_lecture, pattern="^get_"))
    app.add_handler(CallbackQueryHandler(confirm_delete, pattern="^del_"))

    print("✅ البوت شغال!")
    app.run_polling()


if __name__ == "__main__":
    main()
