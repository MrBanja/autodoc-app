from aiogram import types

from bot.sdk.keyboards import MainMenuKeyBoard
from database.models import Order, Document, OrderStatus, UserRole, User


async def get_order_view(orders: list[Order], user: User) -> str:
    text = 'Список заявок:\n'
    for order in orders:
        document = await Document.get(id=order.document_id)
        text += f'№{order.id}. [{OrderStatus.get_str_by_id(order.status_id)}] {document.name}\n'

        if user.role_id == UserRole.ACCOUNTANT:
            text += f'/order_{order.id}\n\n'
    return text


async def list_documents(message: types.Message):
    documents = await Document.get_list(is_deleted=False)
    text = "Список документов:\n"
    for document in documents:
        text += f"№{document.id}. {document.name}\n/document_{document.id}\n\n"
    await message.answer(text)


async def list_workers(message: types.Message, user: User):
    users: list[User] = await User.get_list(role_id=UserRole.WORKER, is_deleted=False)

    text = 'Работники: \n'
    for worker in users:
        text += f'{worker.id}. {worker.username}\n/worker_{worker.id}\n\n'
    await message.answer(
        text,
        reply_markup=await MainMenuKeyBoard.get_reply_markup(user),
    )


async def create_order_by_accountant(message: types.Message, user: User, document: Document, worker: User):
    order = await Order.get_not_completed_order(document_id=document.id, sender_id=worker.id)
    if order:
        await message.answer(
            f"У вас уже есть сформированная заявка №{order.id} на данный документ",
            reply_markup=await MainMenuKeyBoard.get_reply_markup(user),
        )
        return

    order = await Order.create_with_push(
        sender_id=worker.id,
        document_id=document.id,
        receiver_id=user.id,
    )
    await message.answer(
        f"Заявка №{order.id} успешно сформирована",
        reply_markup=await MainMenuKeyBoard.get_reply_markup(user),
    )
