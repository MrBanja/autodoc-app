from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from loguru import logger

from bot.states import FirstInvitation
from bot.sdk.keyboards import MainMenuKeyBoard
from database.models import (
    User, Invitation,
)


async def cmd_start(message: types.Message):
    user = await User.get_by_telegram_id(message.from_user.id)
    if user:
        await message.answer('Вы уже привязаны к предприятию')
        return

    await FirstInvitation.token_enter.set()
    await message.reply("Введите предоставленный вам одноразовый ключ", reply_markup=types.ReplyKeyboardRemove())


async def process_invitation_code(message: types.Message, state: FSMContext):
    invitation = await Invitation.get_by_token(message.text)
    if not invitation:
        await message.answer('Код не верный. Введите еще раз')
        return

    user = await User.get(telegram_id=message.from_user.id)
    if not user:
        user = await User.create(
            telegram_id=message.from_user.id,
            username=invitation.username,
            role_id=invitation.role_id,
            is_deleted=False,
        )
    else:
        await user.update(is_deleted=False)

    logger.info('User registered successfully.')
    await state.finish()

    await message.answer(
        f'{user.username}, добро пожаловать!',
        reply_markup=await MainMenuKeyBoard.get_reply_markup(user),
    )


async def register_handlers(dp: Dispatcher):
    dp.message_handler(commands='start')(cmd_start)
    dp.message_handler(state=FirstInvitation.token_enter)(process_invitation_code)
