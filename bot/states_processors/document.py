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


async def view_document(message: types.Message, regexp_command: Match, user: User):
    doc_id = int(regexp_command.group(1))
    document = await Document.get(id=doc_id, is_deleted=False)
    if not document:
        await message.answer(f"Документ не найден")
        return

    await DocumentView.action.set()
    async with Dispatcher.get_current().current_state().proxy() as data:
        data['document'] = document

    await message.answer(
        f"Документ: {document.name}\nЧто вы хотите сделать?",
        reply_markup=await DocumentActionKeyBoard.get_reply_markup(user),
    )


async def id_delete_document(message: types.Message, user: User, state: FSMContext):
    async with state.proxy() as data:
        document: Document = data['document']
        await state.finish()
        await __delete_doc(document, user, message)


async def ask_for_document(message: types.Message, user: User, state: FSMContext):
    async with state.proxy() as data:
        document = data['document']

    await state.finish()

    if user.role_id == UserRole.ACCOUNTANT:
        await DocumentAskedByWorker.action.set()
        async with Dispatcher.get_current().current_state().proxy() as data:
            data['document'] = document
            await list_workers(message, user)
        return

    order = await Order.get_not_completed_order(document_id=document.id, receiver_id=user.id)
    if order:
        await message.answer(
            f"У вас уже есть сформированная заявка №{order.id} на данный документ",
            reply_markup=await MainMenuKeyBoard.get_reply_markup(user),
        )
        return

    accountant: User = await User.get(role_id=UserRole.ACCOUNTANT, is_deleted=False)  # Fetching any accountant
    order = await Order.create_with_push(
        sender_id=accountant.id,
        document_id=document.id,
        receiver_id=user.id,
    )
    await message.answer(
        f"Заявка №{order.id} успешно сформирована",
        reply_markup=await MainMenuKeyBoard.get_reply_markup(user),
    )


async def ask_for_document_by_accountant(message: types.Message, user: User, state: FSMContext, regexp_command: Match):
    doc_id = int(regexp_command.group(1))
    document = await Document.get(id=doc_id, is_deleted=False)
    if not document:
        await message.answer(f"Документ не найден")
        return

    async with state.proxy() as data:
        worker: User = data.get('worker')

    await state.finish()
    await create_order_by_accountant(message, user, document, worker)


async def manage_start_document(message: types.Message, user: User):
    await DocumentManageView.action.set()

    await message.answer(
        f"Выберете, что сделать",
        reply_markup=await DocumentManageActionKeyBoard.get_reply_markup(user),
    )


async def manage_delete_document(message: types.Message, state: FSMContext):
    await state.finish()
    await DocumentManageDeleteView.document_name.set()
    await message.answer(
        f"Введите название документа",
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True).add("Отмена"),
    )


async def manage_finish_delete_document(message: types.Message, state: FSMContext, user: User):
    document: Document = await Document.get(name=message.text, is_deleted=False)
    if not document:
        await message.answer("Документ не найден")
        return

    await state.finish()
    await __delete_doc(document, user, message)


async def manage_add_document(message: types.Message, state: FSMContext):
    await state.finish()
    await DocumentManageAddView.document_name.set()
    await message.answer(
        f"Введите название документа",
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True).add("Отмена"),
    )


async def manage_finish_add_document(message: types.Message, state: FSMContext, user: User):
    if len(message.text) < 3:
        await message.answer("Название слишком короткое, введите снова")
        return

    document: Document = await Document.get(name=message.text)
    if document and not document.is_deleted:
        await message.answer("Такой документ уже существует")
        return

    if document and document.is_deleted:
        new_doc = await document.update(is_deleted=False)
    else:
        new_doc = await Document.create(name=message.text)

    await state.finish()
    await message.answer(
        f"Документ {new_doc.name} успешно создан.\n/document_{new_doc.id}",
        reply_markup=await MainMenuKeyBoard.get_reply_markup(user),
    )


async def __delete_doc(document: Document, user: User, message: types.Message):
    orders: list[Order] = await Order.get_list_for_view(
        statuses=(OrderStatus.NEW, OrderStatus.PROCESSING, OrderStatus.READY),
        document_id=document.id,
    )
    if orders:
        text = f"Документ {document.name} не может быть удален. У него остались активные заявки:\n"
        for order in orders:
            text += f'№{order.id}\t\t/order_{order.id}\n'

        await message.answer(
            text,
            reply_markup=await MainMenuKeyBoard.get_reply_markup(user),
        )
        return

    await document.update(is_deleted=True)
    await message.answer(
        f"Документ {document.name} успешно удален",
        reply_markup=await MainMenuKeyBoard.get_reply_markup(user),
    )


async def register_handlers(dp: Dispatcher):
    dp.message_handler(
        Text(equals=MainMenuKeyBoard.Button.doc_list.value),
        AuthorizedUser(),
    )(list_documents)
    dp.message_handler(
        RegexpCommandsFilter(regexp_commands=[r'document_(\d+)$']),
        AuthorizedUser(return_user=True),
    )(view_document)
    dp.message_handler(
        Text(DocumentActionKeyBoard.Button.ask.value),
        AuthorizedUser(return_user=True),
        state=DocumentView.action,
    )(ask_for_document)
    dp.message_handler(
        Text(DocumentActionKeyBoard.Button.admin_delete.value),
        AuthorizedUser(return_user=True, user_role=UserRole.ACCOUNTANT),
        state=DocumentView.action,
    )(id_delete_document)

    dp.message_handler(
        Text(MainMenuKeyBoard.Button.admin_manage_doc.value),
        AuthorizedUser(return_user=True, user_role=UserRole.ACCOUNTANT),
    )(manage_start_document)

    dp.message_handler(
        Text(DocumentManageActionKeyBoard.Button.delete.value),
        AuthorizedUser(user_role=UserRole.ACCOUNTANT),
        state=DocumentManageView.action,
    )(manage_delete_document)
    dp.message_handler(
        not_cancel,
        AuthorizedUser(return_user=True, user_role=UserRole.ACCOUNTANT),
        state=DocumentManageDeleteView.document_name,
    )(manage_finish_delete_document)

    dp.message_handler(
        Text(DocumentManageActionKeyBoard.Button.add.value),
        AuthorizedUser(user_role=UserRole.ACCOUNTANT),
        state=DocumentManageView.action,
    )(manage_add_document)
    dp.message_handler(
        not_cancel,
        AuthorizedUser(return_user=True, user_role=UserRole.ACCOUNTANT),
        state=DocumentManageAddView.document_name,
    )(manage_finish_add_document)

    dp.message_handler(
        RegexpCommandsFilter(regexp_commands=[r'document_(\d+)$']),
        AuthorizedUser(return_user=True, user_role=UserRole.ACCOUNTANT),
        state=WorkerAskDocument.document,
    )(ask_for_document_by_accountant)
