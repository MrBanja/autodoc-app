import asyncio

import aio_pika
import alembic.command
import alembic.command
import alembic.config
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.utils import executor
from alembic.util import CommandError
from loguru import logger

from bot.sdk.filters import AuthorizedUser
from bot.sdk.keyboards import MainMenuKeyBoard
from bot.states_processors.document import register_handlers as view_doc_handlers
from bot.states_processors.invitation import register_handlers as inv_reg_handlers
from bot.states_processors.order import register_handlers as order_handlers
from bot.states_processors.worker import register_handlers as worker_handlers
from database.aiogram_storage import storage
from database.models import User
from utils.config import get_config, AppConfig

bot = Bot(token=get_config().telegram.tg_token)

dp = Dispatcher(bot, storage=storage)


async def unknown(message: types.Message):
    await message.reply(f'Неизвестная команда', reply_markup=types.ReplyKeyboardRemove())


async def unknown_on_state(message: types.Message):
    await message.reply(f'Неизвестная команда')


async def unknown_authorized(message: types.Message, user: User):
    await message.answer(f'Неизвестная команда', reply_markup=await MainMenuKeyBoard.get_reply_markup(user))


async def cancel_handler(message: types.Message, state: FSMContext, user: User):
    current_state = await state.get_state()
    if current_state is None:
        return

    logger.info(f'Cancelling state {current_state}')
    await state.finish()
    await message.reply('Отменено', reply_markup=await MainMenuKeyBoard.get_reply_markup(user))


async def __system_clear_keyboard(message: types.Message):
    await message.reply('...', reply_markup=types.ReplyKeyboardRemove())


async def __system_current_state(message: types.Message, state: FSMContext):
    state = await state.get_state()
    await message.reply(f'Состояние {state if state else "отсутствует"}')


async def register_handler():
    await inv_reg_handlers(dp)
    await view_doc_handlers(dp)
    await order_handlers(dp)
    await worker_handlers(dp)

    dp.message_handler(AuthorizedUser(return_user=True), state='*', commands='cancel')(cancel_handler)
    dp.message_handler(
        AuthorizedUser(return_user=True),
        Text(equals='Отмена', ignore_case=True),
        state='*',
    )(cancel_handler)

    dp.message_handler(commands='__clear_key_board')(__system_clear_keyboard)
    dp.message_handler(commands='__current_state', state='*')(__system_current_state)
    dp.message_handler(AuthorizedUser(return_user=True))(unknown_authorized)
    dp.message_handler(state='*')(unknown_on_state)
    dp.message_handler()(unknown)


def run_alembic(cfg: AppConfig) -> None:
    """Apply migrations to target DB."""
    if cfg.migrate_to is None:
        logger.warning("Alembic migrations are disabled by config")
    else:
        logger.info(
            f"Applying alembic migration <{cfg.migrate_to}>...",
        )

        alembic_conf = alembic.config.Config("alembic.ini")
        alembic_conf.attributes["configure_logger"] = False
        alembic_conf.set_main_option(
            "sqlalchemy.url",
            cfg.db.uri('postgresql'),
        )
        try:
            alembic.command.upgrade(alembic_conf, cfg.migrate_to)
        except CommandError:
            alembic.command.downgrade(alembic_conf, cfg.migrate_to)
        logger.info("...finished applying migrations")


async def on_startup(*_):
    settings = get_config()
    run_alembic(settings)
    await bot.set_webhook(settings.telegram.webhook)
    connection: aio_pika.connection.AbstractConnection = await aio_pika.connect_robust(
        host=settings.rmq.host,
        virtualhost=settings.rmq.vhost,
        login=settings.rmq.username,
        password=settings.rmq.password.get_secret_value(),
        loop=asyncio.get_running_loop(),
    )

    channel: aio_pika.channel.AbstractChannel = await connection.channel()
    # await storage.set_data(user='storage', chat='connection', data=dict(channel=channel))
    storage.data['rmq_channel'] = dict(channel=channel)


async def on_shutdown(dispatcher: Dispatcher):
    logger.warning('Shutting down..')
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(register_handler())
    config = get_config()
    executor.start_webhook(
        dispatcher=dp,
        webhook_path='',
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=config.telegram.host,
        port=config.telegram.port,
    )


if __name__ == '__main__':
    main()
