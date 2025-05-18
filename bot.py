import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters, CallbackQueryHandler,
    ConversationHandler
)
from datetime import datetime
import csv
import io
#ff
# Логирование
logging.basicConfig(level=logging.INFO)

# Состояния для ConversationHandler
(
    ADD_ACCOUNT_NAME, ADD_ACCOUNT_TYPE, ADD_ACCOUNT_CURRENCY, ADD_ACCOUNT_BALANCE,
    ADD_INCOME_AMOUNT, ADD_INCOME_CATEGORY, ADD_INCOME_ACCOUNT,
    ADD_EXPENSE_AMOUNT, ADD_EXPENSE_CATEGORY, ADD_EXPENSE_ACCOUNT
) = range(10)

# Старт
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("Добавить счёт"), KeyboardButton("Добавить доход")],
        [KeyboardButton("Добавить расход")],
        [KeyboardButton("Показать баланс")],
        [KeyboardButton("Статистика"), KeyboardButton("Сохранить статистику")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Привет! Я бот для ведения бюджета. Выбери действие:", reply_markup=reply_markup)

# === ДОБАВЛЕНИЕ СЧЕТА ===
async def start_add_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи название счёта:")
    return ADD_ACCOUNT_NAME

async def add_account_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_account'] = {'name': update.message.text}
    await update.message.reply_text("Введи тип счёта (например: дебетовый, вклад, накопительный):")
    return ADD_ACCOUNT_TYPE

async def add_account_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_account']['type'] = update.message.text
    await update.message.reply_text("Укажи валюту счёта (например: RUB, USD):")
    return ADD_ACCOUNT_CURRENCY

async def add_account_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_account']['currency'] = update.message.text.upper()
    await update.message.reply_text("Введи текущий баланс:")
    return ADD_ACCOUNT_BALANCE

async def add_account_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        balance = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Неверный формат. Введи число.")
        return ADD_ACCOUNT_BALANCE

    context.user_data['new_account']['balance'] = balance
    account = context.user_data['new_account']

    if 'accounts' not in context.user_data:
        context.user_data['accounts'] = []
    context.user_data['accounts'].append(account)

    await update.message.reply_text(f"Счёт {account['name']} добавлен!")
    return ConversationHandler.END

# === ДОБАВЛЕНИЕ ДОХОДА ===
async def start_add_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи сумму дохода:")
    return ADD_INCOME_AMOUNT

async def add_income_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['new_income'] = {'amount': float(update.message.text)}
        await update.message.reply_text("Укажи категорию дохода:")
        return ADD_INCOME_CATEGORY
    except ValueError:
        await update.message.reply_text("Неверный формат. Введи число.")
        return ADD_INCOME_AMOUNT

async def add_income_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_income']['category'] = update.message.text
    accounts = context.user_data.get('accounts', [])

    if not accounts:
        await update.message.reply_text("Нет добавленных счетов. Сначала добавь счёт.")
        return ConversationHandler.END

    buttons = [[InlineKeyboardButton(f"{i+1}. {acc['name']} ({acc['type']})", callback_data=str(i))] for i, acc in enumerate(accounts)]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Выбери счёт, на который зачислить доход:", reply_markup=reply_markup)
    return ADD_INCOME_ACCOUNT

async def add_income_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    index = int(query.data)
    account = context.user_data['accounts'][index]
    income = context.user_data['new_income']

    # Добавляем сумму к балансу
    account['balance'] += income['amount']

    # Записываем операцию
    if 'incomes' not in context.user_data:
        context.user_data['incomes'] = []
    context.user_data['incomes'].append({
        'amount': income['amount'],
        'category': income['category'],
        'account': account['name'],
        'date': datetime.now()
    })

    await query.edit_message_text(f"Доход {income['amount']} {account['currency']} добавлен на счёт {account['name']}.")
    return ConversationHandler.END

# === ДОБАВЛЕНИЕ РАСХОДА ===
async def start_add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи сумму расхода:")
    return ADD_EXPENSE_AMOUNT

async def add_expense_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['new_expense'] = {'amount': float(update.message.text)}
        await update.message.reply_text("Укажи категорию расхода:")
        return ADD_EXPENSE_CATEGORY
    except ValueError:
        await update.message.reply_text("Неверный формат. Введи число.")
        return ADD_EXPENSE_AMOUNT

async def add_expense_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_expense']['category'] = update.message.text
    accounts = context.user_data.get('accounts', [])

    if not accounts:
        await update.message.reply_text("Нет добавленных счетов. Сначала добавь счёт.")
        return ConversationHandler.END

    buttons = [[InlineKeyboardButton(f"{i+1}. {acc['name']} ({acc['type']})", callback_data=str(i))] for i, acc in enumerate(accounts)]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Выбери счёт, с которого списать расход:", reply_markup=reply_markup)
    return ADD_EXPENSE_ACCOUNT

async def add_expense_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    index = int(query.data)
    account = context.user_data['accounts'][index]
    expense = context.user_data['new_expense']

    # Проверяем, достаточно ли средств
    if account['balance'] < expense['amount']:
        await query.edit_message_text(f"Недостаточно средств на счёте {account['name']}. Текущий баланс: {account['balance']}")
        return ConversationHandler.END

    # Вычитаем сумму из баланса
    account['balance'] -= expense['amount']

    # Записываем операцию
    if 'expenses' not in context.user_data:
        context.user_data['expenses'] = []
    context.user_data['expenses'].append({
        'amount': expense['amount'],
        'category': expense['category'],
        'account': account['name'],
        'date': datetime.now()
    })

    await query.edit_message_text(f"Расход {expense['amount']} {account['currency']} списан со счёта {account['name']}.")
    return ConversationHandler.END

# === ПОКАЗАТЬ БАЛАНС ===
async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    accounts = context.user_data.get('accounts', [])
    if not accounts:
        await update.message.reply_text("Нет добавленных счетов.")
        return
    text = "Баланс по счетам:\n"
    for acc in accounts:
        text += f"{acc['name']} ({acc['type']}), валюта {acc['currency']}: {acc['balance']:.2f}\n"
    await update.message.reply_text(text)

# === СТАТИСТИКА ===
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    incomes = context.user_data.get('incomes', [])
    expenses = context.user_data.get('expenses', [])

    if not incomes and not expenses:
        await update.message.reply_text("Данных по операциям ещё нет.")
        return

    def summarize(ops):
        summary = {}
        for op in ops:
            cat = op['category']
            summary[cat] = summary.get(cat, 0) + op['amount']
        return summary

    inc_sum = summarize(incomes)
    exp_sum = summarize(expenses)

    text = "📊 Статистика доходов:\n"
    if inc_sum:
        for cat, val in inc_sum.items():
            text += f"- {cat}: {val:.2f}\n"
    else:
        text += "нет данных\n"

    text += "\n📉 Статистика расходов:\n"
    if exp_sum:
        for cat, val in exp_sum.items():
            text += f"- {cat}: {val:.2f}\n"
    else:
        text += "нет данных\n"

    await update.message.reply_text(text)

# === СОХРАНИТЬ СТАТИСТИКУ В CSV ===
async def save_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    incomes = context.user_data.get('incomes', [])
    expenses = context.user_data.get('expenses', [])

    if not incomes and not expenses:
        await update.message.reply_text("Данных по операциям ещё нет.")
        return

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Тип', 'Сумма', 'Категория', 'Счёт', 'Дата'])

    for op in incomes:
        writer.writerow(['Доход', f"{op['amount']:.2f}", op['category'], op['account'], op['date'].strftime("%Y-%m-%d %H:%M:%S")])
    for op in expenses:
        writer.writerow(['Расход', f"{op['amount']:.2f}", op['category'], op['account'], op['date'].strftime("%Y-%m-%d %H:%M:%S")])

    output.seek(0)
    await update.message.reply_document(document=output, filename="statistics.csv")

# Обработчик текста кнопок меню
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Добавить счёт":
        return await start_add_account(update, context)
    elif text == "Добавить доход":
        return await start_add_income(update, context)
    elif text == "Добавить расход":
        return await start_add_expense(update, context)
    elif text == "Показать баланс":
        await show_balance(update, context)
    elif text == "Статистика":
        await stats(update, context)
    elif text == "Сохранить статистику":
        await save_stats(update, context)
    else:
        await update.message.reply_text("Я не понял. Пожалуйста, используй кнопки или команды.")

# === ConversationHandler для добавления счета
add_account_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^Добавить счёт$"), start_add_account)],
    states={
        ADD_ACCOUNT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_name)],
        ADD_ACCOUNT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_type)],
        ADD_ACCOUNT_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_currency)],
        ADD_ACCOUNT_BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_balance)],
    },
    fallbacks=[],
)

# === ConversationHandler для добавления дохода
add_income_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^Добавить доход$"), start_add_income)],
    states={
        ADD_INCOME_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_income_amount)],
        ADD_INCOME_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_income_category)],
        ADD_INCOME_ACCOUNT: [CallbackQueryHandler(add_income_account)],
    },
    fallbacks=[],
)

# === ConversationHandler для добавления расхода
add_expense_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^Добавить расход$"), start_add_expense)],
    states={
        ADD_EXPENSE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense_amount)],
        ADD_EXPENSE_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense_category)],
        ADD_EXPENSE_ACCOUNT: [CallbackQueryHandler(add_expense_account)],
    },
    fallbacks=[],
)

# Основная точка входа
def main():
    app = ApplicationBuilder().token("7825702092:AAGKyGr_oY9dgtoimkGvc0UDd11Nz5Mx7iM").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(add_account_conv)
    app.add_handler(add_income_conv)
    app.add_handler(add_expense_conv)
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("save_stats", save_stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling()

if __name__ == '__main__':
    main()
