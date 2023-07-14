from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import TOKEN
from models import Base, User, Task, Subject

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

engine = create_engine('sqlite:///homework_bot.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Start command
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    if user is None:
        user = User(telegram_id=message.from_user.id, nickname=message.from_user.username)
        session.add(user)
        session.commit()
        await message.answer(f"Welcome to Homework Bot, {user.nickname}!")
    else:
        await message.answer(f"Welcome back, {user.nickname}!")

# Upload task command
class UploadTask(StatesGroup):
    waiting_for_image = State()
    waiting_for_school = State()
    waiting_for_grade = State()
    waiting_for_date = State()
    waiting_for_tags = State()

@dp.message_handler(commands=['upload'])
async def upload_task_step1(message: types.Message):
    await message.answer("Please upload an image of your homework solution.")
    await UploadTask.waiting_for_image.set()

@dp.message_handler(content_types=['photo'], state=UploadTask.waiting_for_image)
async def upload_task_step2(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    file_id = photo.file_id
    await state.update_data(file_id=file_id)
    await message.answer("Please enter the name of your school.")
    await UploadTask.waiting_for_school.set()

@dp.message_handler(state=UploadTask.waiting_for_school)
async def upload_task_step3(message: types.Message, state: FSMContext):
    school = message.text
    await state.update_data(school=school)
    await message.answer("Please enter your grade.")
    await UploadTask.waiting_for_grade.set()

@dp.message_handler(state=UploadTask.waiting_for_grade)
async def upload_task_step4(message: types.Message, state: FSMContext):
    grade = message.text
    await state.update_data(grade=grade)
    await message.answer("Please enter the date of your homework solution (YYYY-MM-DD).")
    await UploadTask.waiting_for_date.set()

@dp.message_handler(state=UploadTask.waiting_for_date)
async def upload_task_step5(message: types.Message, state: FSMContext):
    date = message.text
    await state.update_data(date=date)
    await message.answer("Please enter the tags for your homework solution, separated by commas.")
    await UploadTask.waiting_for_tags.set()

@dp.message_handler(state=UploadTask.waiting_for_tags)
async def upload_task_step6(message: types.Message, state: FSMContext):
    tags = message.text.split(",")
    file_id = (await state.get_data())['file_id']
    task = Task(school=(await state.get_data())['school'], grade=(await state.get_data())['grade'],
                date=(await state.get_data())['date'], tags=tags, image=file_id, likes=0, dislikes=0)
    session.add(task)
    session.commit()
    await message.answer("Your homework solution has been uploaded successfully!")
    await state.finish()

# Search task command
@dp.message_handler(commands=['search'])
async def search_task_step1(message: types.Message):
    subjects = session.query(Subject).all()
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for subject in subjects:
        keyboard.add(KeyboardButton(subject.name))
    await message.answer("Please select a subject:", reply_markup=keyboard)

@dp.message_handler(Text(equals=[subject.name for subject in session.query(Subject).all()]))
async def search_task_step2(message: types.Message):
    subject = session.query(Subject).filter_by(name=message.text).first()
    tasks = subject.search_tasks(session.query(Task).all())
    if len(tasks) == 0:
        await message.answer("No homework solutions found.")
    else:
        for task in tasks:
            await bot.send_photo(chat_id=message.chat.id, photo=task.image, caption=f"School: {task.school}\nGrade: {task.grade}\nDate: {task.date}\nTags: {', '.join(task.tags)}\nLikes: {task.likes}\nDislikes: {task.dislikes}")

# Load task command
@dp.message_handler(commands=['load'])
async def load_task_step1(message: types.Message):
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    if user.internal_currency_balance == 0:
        await message.answer("You don't have enough SH to load a homework solution.")
    else:
        tasks = session.query(Task).all()
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        for task in tasks:
            keyboard.add(KeyboardButton(f"{task.school} {task.grade} {task.date}"))
        await message.answer("Please select a homework solution to load:", reply_markup=keyboard)
        await LoadTask.waiting_for_task.set()

class LoadTask(StatesGroup):
    waiting_for_task = State()

@dp.message_handler(Text(equals=[f"{task.school} {task.grade} {task.date}" for task in session.query(Task).all()]), state=LoadTask.waiting_for_task)
async def load_task_step2(message: types.Message, state: FSMContext):
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    task = session.query(Task).filter_by(school=message.text.split()[0], grade=message.text.split()[1], date=message.text.split()[2]).first()
    user.load_task(task)
    session.commit()
    await message.answer("Homework solution loaded successfully!")
    await state.finish()

# Buy SH command
@dp.message_handler(commands=['buy'])
async def buy_sh_step1(message: types.Message):
    await message.answer("Please enter the number of SH you want to buy.")
    await BuySH.waiting_for_sh.set()

class BuySH(StatesGroup):
    waiting_for_sh = State()

@dp.message_handler(state=BuySH.waiting_for_sh)
async def buy_sh_step2(message: types.Message, state: FSMContext):
    sh = int(message.text)
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    user.buy_sh(sh)
    session.commit()
    await message.answer(f"{sh} SH purchased successfully!")
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
