# utils/functions.py

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
import random


functions_router = Router()


@functions_router.callback_query(F.data == "close_callback")
async def close_settings(call: CallbackQuery):
    await call.message.delete()
    