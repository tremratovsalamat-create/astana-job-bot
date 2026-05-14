import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from database import Database
from parser import HHParser
from config import BOT_TOKEN, JOBS_PER_PAGE

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for ConversationHandler
WAITING_RESUME = 1

db = Database()
parser = HHParser()


def get_main_keyboard():
    keyboard = [
        [KeyboardButton("🔍 Поиск вакансий"), KeyboardButton("⭐ Сохранённые")],
        [KeyboardButton("📄 Мои резюме"), KeyboardButton("🏙 Популярные профессии")],
        [KeyboardButton("ℹ️ Помощь")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username or "", user.first_name or "")
    
    text = (
        f"👋 Привет, *{user.first_name}*!\n\n"
        "Я помогу тебе найти работу в Астане прямо здесь, в Telegram.\n\n"
        "🔍 Введи название профессии или нажми *«Популярные профессии»*.\n\n"
        "📌 Данные берутся с hh.kz в реальном времени."
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=get_main_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *Как пользоваться ботом:*\n\n"
        "🔍 *Поиск вакансий* — введи профессию, например: `Python разработчик`\n"
        "⭐ *Сохранённые* — вакансии, которые ты лайкнул\n"
        "📄 *Мои резюме* — загрузи своё резюме (PDF)\n"
        "🏙 *Популярные профессии* — быстрый выбор популярных вакансий\n\n"
        "👍 *Лайк* — сохранить вакансию\n"
        "👎 *Дизлайк* — пропустить вакансию\n"
        "➡️ *Следующая* — показать следующую вакансию"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def search_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 Введите название профессии или должности:\n\n"
        "Например: *Python разработчик*, *Менеджер*, *Дизайнер*",
        parse_mode="Markdown"
    )
    context.user_data["searching"] = True


async def popular_professions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("💻 Python разработчик", callback_data="search:Python разработчик"),
            InlineKeyboardButton("📊 Аналитик данных", callback_data="search:Аналитик данных"),
        ],
        [
            InlineKeyboardButton("🎨 UI/UX Дизайнер", callback_data="search:UI UX дизайнер"),
            InlineKeyboardButton("📱 Менеджер проекта", callback_data="search:Менеджер проекта"),
        ],
        [
            InlineKeyboardButton("🏦 Финансист", callback_data="search:Финансист"),
            InlineKeyboardButton("⚙️ DevOps инженер", callback_data="search:DevOps инженер"),
        ],
        [
            InlineKeyboardButton("📞 Менеджер по продажам", callback_data="search:Менеджер по продажам"),
            InlineKeyboardButton("🧑‍⚕️ Медсестра", callback_data="search:Медсестра"),
        ],
        [
            InlineKeyboardButton("🏗 Инженер", callback_data="search:Инженер"),
            InlineKeyboardButton("📝 Бухгалтер", callback_data="search:Бухгалтер"),
        ],
    ]
    await update.message.reply_text(
        "🏙 *Популярные профессии в Астане:*\n\nВыберите одну из профессий:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def saved_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    jobs = db.get_saved_jobs(user_id)
    
    if not jobs:
        await update.message.reply_text(
            "⭐ У тебя пока нет сохранённых вакансий.\n\n"
            "Нажми 👍 чтобы сохранить понравившуюся вакансию!"
        )
        return
    
    text = f"⭐ *Твои сохранённые вакансии ({len(jobs)}):*\n\n"
    keyboard = []
    
    for i, job in enumerate(jobs[:10], 1):
        text += f"{i}. *{job['title']}*\n   🏢 {job['company']}\n   💰 {job['salary']}\n\n"
        keyboard.append([InlineKeyboardButton(
            f"🗑 Удалить: {job['title'][:30]}...", 
            callback_data=f"unsave:{job['job_id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔍 Найти ещё вакансии", callback_data="go_search")])
    
    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def my_resumes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    resumes = db.get_resumes(user_id)
    
    keyboard = [[InlineKeyboardButton("📎 Загрузить резюме (PDF)", callback_data="upload_resume")]]
    
    if resumes:
        text = f"📄 *Твои резюме ({len(resumes)}):*\n\n"
        for i, r in enumerate(resumes, 1):
            text += f"{i}. 📄 {r['filename']} — {r['uploaded_at'][:10]}\n"
        text += "\n_Загрузи новое резюме в формате PDF_"
    else:
        text = "📄 У тебя ещё нет загруженных резюме.\n\nЗагрузи своё резюме в формате PDF!"
    
    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    # Handle menu buttons
    if text == "🔍 Поиск вакансий":
        await search_jobs(update, context)
        return
    elif text == "⭐ Сохранённые":
        await saved_jobs(update, context)
        return
    elif text == "📄 Мои резюме":
        await my_resumes(update, context)
        return
    elif text == "🏙 Популярные профессии":
        await popular_professions(update, context)
        return
    elif text == "ℹ️ Помощь":
        await help_command(update, context)
        return
    
    # Treat any other text as job search query
    await perform_search(update, context, text)


async def perform_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    user_id = update.effective_user.id
    
    msg = await update.message.reply_text(
        f"⏳ Ищу вакансии по запросу *«{query}»*...\n\n_Подождите несколько секунд_",
        parse_mode="Markdown"
    )
    
    try:
        jobs = parser.search_jobs(query, city="Астана")
        
        if not jobs:
            await msg.edit_text(
                f"😔 По запросу *«{query}»* вакансий не найдено.\n\n"
                "Попробуй другой запрос или выбери из популярных профессий.",
                parse_mode="Markdown"
            )
            return
        
        # Filter seen jobs
        seen_ids = db.get_seen_jobs(user_id)
        new_jobs = [j for j in jobs if j["id"] not in seen_ids]
        
        if not new_jobs:
            new_jobs = jobs  # If all seen, show again
        
        # Store in context
        context.user_data["jobs"] = new_jobs
        context.user_data["job_index"] = 0
        context.user_data["query"] = query
        
        await msg.delete()
        await show_job(update, context, new_jobs[0], 0, len(new_jobs))
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        await msg.edit_text(
            "❌ Ошибка при поиске. Попробуйте позже.\n\n"
            "Возможно, hh.kz временно недоступен.",
        )


async def show_job(update: Update, context: ContextTypes.DEFAULT_TYPE, job: dict, index: int, total: int):
    user_id = update.effective_user.id if update.message else update.callback_query.from_user.id
    
    # Mark as seen
    db.mark_seen(user_id, job["id"])
    
    text = (
        f"📋 *{job['title']}*\n\n"
        f"🏢 *Компания:* {job['company']}\n"
        f"💰 *Зарплата:* {job['salary']}\n"
        f"📍 *Город:* {job.get('city', 'Астана')}\n"
        f"🕐 *Опыт:* {job.get('experience', 'Не указан')}\n"
        f"📅 *Размещено:* {job.get('date', 'Недавно')}\n\n"
        f"📝 *Описание:*\n{job.get('description', 'Нет описания')[:400]}...\n\n"
        f"_Вакансия {index + 1} из {total}_"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("👍 Сохранить", callback_data=f"like:{job['id']}"),
            InlineKeyboardButton("👎 Пропустить", callback_data=f"dislike:{job['id']}"),
        ],
        [
            InlineKeyboardButton("🔗 Открыть на hh.kz", url=job.get("url", "https://hh.kz")),
        ],
        [
            InlineKeyboardButton("➡️ Следующая", callback_data="next_job"),
            InlineKeyboardButton("🔍 Новый поиск", callback_data="go_search"),
        ],
    ]
    
    if update.message:
        await update.message.reply_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )
    else:
        await update.callback_query.message.reply_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith("search:"):
        profession = data.split(":", 1)[1]
        await query.message.reply_text(f"🔍 Ищу: *{profession}*...", parse_mode="Markdown")
        
        # Simulate message for perform_search
        class FakeUpdate:
            message = query.message
            effective_user = query.from_user
        
        await perform_search(FakeUpdate(), context, profession)
    
    elif data == "next_job":
        jobs = context.user_data.get("jobs", [])
        index = context.user_data.get("job_index", 0) + 1
        
        if index >= len(jobs):
            await query.message.reply_text(
                "🔚 Вакансии закончились!\n\n"
                "Хочешь поискать по другому запросу?",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔍 Новый поиск", callback_data="go_search"),
                    InlineKeyboardButton("🏙 Популярные", callback_data="go_popular"),
                ]])
            )
            return
        
        context.user_data["job_index"] = index
        await show_job(update, context, jobs[index], index, len(jobs))
    
    elif data.startswith("like:"):
        job_id = data.split(":", 1)[1]
        jobs = context.user_data.get("jobs", [])
        job = next((j for j in jobs if j["id"] == job_id), None)
        
        if job:
            db.save_job(user_id, job)
            await query.message.reply_text("⭐ Вакансия сохранена!")
        
        # Auto-advance
        index = context.user_data.get("job_index", 0) + 1
        if index < len(jobs):
            context.user_data["job_index"] = index
            await show_job(update, context, jobs[index], index, len(jobs))
    
    elif data.startswith("dislike:"):
        jobs = context.user_data.get("jobs", [])
        index = context.user_data.get("job_index", 0) + 1
        
        if index < len(jobs):
            context.user_data["job_index"] = index
            await show_job(update, context, jobs[index], index, len(jobs))
        else:
            await query.message.reply_text(
                "🔚 Больше вакансий нет. Попробуй другой поиск!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔍 Новый поиск", callback_data="go_search")
                ]])
            )
    
    elif data.startswith("unsave:"):
        job_id = data.split(":", 1)[1]
        db.unsave_job(user_id, job_id)
        await query.message.reply_text("🗑 Вакансия удалена из сохранённых.")
    
    elif data == "go_search":
        await query.message.reply_text(
            "🔍 Введите название профессии:",
            reply_markup=get_main_keyboard()
        )
    
    elif data == "go_popular":
        keyboard = [
            [
                InlineKeyboardButton("💻 Python разработчик", callback_data="search:Python разработчик"),
                InlineKeyboardButton("📊 Аналитик данных", callback_data="search:Аналитик данных"),
            ],
            [
                InlineKeyboardButton("🎨 Дизайнер", callback_data="search:Дизайнер"),
                InlineKeyboardButton("📱 Менеджер", callback_data="search:Менеджер"),
            ],
        ]
        await query.message.reply_text(
            "🏙 Выберите профессию:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "upload_resume":
        await query.message.reply_text(
            "📎 Отправь своё резюме в формате *PDF*.\n\n"
            "Я сохраню его в твоём профиле.",
            parse_mode="Markdown"
        )
        context.user_data["waiting_resume"] = True


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    doc = update.message.document
    
    if doc.mime_type != "application/pdf":
        await update.message.reply_text(
            "❌ Пожалуйста, загрузи файл в формате *PDF*.",
            parse_mode="Markdown"
        )
        return
    
    if doc.file_size > 5 * 1024 * 1024:  # 5MB limit
        await update.message.reply_text("❌ Файл слишком большой. Максимум 5MB.")
        return
    
    file = await context.bot.get_file(doc.file_id)
    
    # Save to database
    db.save_resume(user_id, doc.file_id, doc.file_name or "resume.pdf")
    
    await update.message.reply_text(
        f"✅ Резюме *{doc.file_name}* успешно сохранено!\n\n"
        "Ты можешь загрузить несколько резюме.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не установлен в config.py или .env")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("saved", saved_jobs))
    app.add_handler(CommandHandler("search", search_jobs))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    # Documents (resume upload)
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("🤖 Astana Jobs Bot запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
