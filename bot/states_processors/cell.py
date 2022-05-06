from typing import Match

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text, RegexpCommandsFilter

from bot.sdk.common import list_documents, list_workers, create_order_by_accountant
from bot.sdk.filters import AuthorizedUser, not_cancel
from bot.sdk.keyboards import MainMenuKeyBoard, DocumentActionKeyBoard, DocumentManageActionKeyBoard
from bot.states import DocumentView, DocumentManageView, DocumentManageAddView, DocumentManageDeleteView, \
    WorkerAskDocument, DocumentAskedByWorker
from database.models import (
    User, Document, Order, OrderStatus, UserRole,
)


async def register_handlers(dp: Dispatcher):
    dp.message_handler(
        Text(equals=MainMenuKeyBoard.Button.doc_list.value),
        AuthorizedUser(),
    )(list_documents)
