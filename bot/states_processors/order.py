from typing import Match

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text, RegexpCommandsFilter

from bot.sdk.common import get_order_view
from bot.sdk.filters import AuthorizedUser
from bot.sdk.keyboards import MainMenuKeyBoard, OrderViewTypeKeyBoard, OrderActionKeyBoard, OrderViewToKeyBoard, \
    OrderDetailedViewKeyBoard, OrderChangeStatusKeyBoard
from bot.states import OrderView, OrderMain, OrderDetailedView
from database.models import (
    User, Document, Order, OrderStatus, UserRole,
)
from utils.functions import get_all_enum_values


async def start_order_main_menu(message: types.Message, user: User):
    await OrderMain.action.set()
    await message.answer(
        "Что вы хотите сделать?",
        reply_markup=await OrderActionKeyBoard.get_reply_markup(user),
    )


async def view_order_type_menu(message: types.Message, user: User, state: FSMContext):
    await state.finish()
    await OrderView.type.set()
    await message.answer(
        "Активные или Завершенные?",
        reply_markup=await OrderViewTypeKeyBoard.get_reply_markup(user),
    )


async def view_order_to_menu(message: types.Message, user: User, state: FSMContext):
    await OrderView.to.set()
    async with state.proxy() as data:
        if message.text == OrderViewTypeKeyBoard.Button.new:
            data['statuses'] = OrderStatus.NEW, OrderStatus.PROCESSING, OrderStatus.READY
        elif message.text == OrderViewTypeKeyBoard.Button.old:
            data['statuses'] = OrderStatus.DONE, OrderStatus.DECLINED

    await message.answer(
        "От вас или вам?",
        reply_markup=await OrderViewToKeyBoard.get_reply_markup(user),
    )


async def view_order_show(message: types.Message, user: User, state: FSMContext):
    async with state.proxy() as data:
        if message.text == OrderViewToKeyBoard.Button.to_me:
            data['receiver_id'] = user.id
        else:
            data['sender_id'] = user.id

        text = 'Список заявок:\n'
        orders = await Order.get_list_for_view(**data)
        text = await get_order_view(orders, user)
        await message.answer(
            text,
            reply_markup=await MainMenuKeyBoard.get_reply_markup(user),
        )
    await state.finish()


async def view_single_order(message: types.Message, regexp_command: Match, user: User):
    order_id = int(regexp_command.group(1))
    order: Order = await Order.get(id=order_id)
    if not order:
        await message.answer(f"Заявки не найден")
        return

    document = await Document.get(id=order.document_id)
    text = f'Заявка №{order.id}. [{OrderStatus.get_str_by_id(order.status_id)}] {document.name}\n'

    if order.sender_id == user.id and order.status_id in {OrderStatus.NEW, OrderStatus.PROCESSING}:
        pass
    elif order.receiver_id == user.id and order.status_id == OrderStatus.READY:
        pass

    if user.role_id != UserRole.ACCOUNTANT:
        await message.answer(
            text,
            reply_markup=await MainMenuKeyBoard.get_reply_markup(user),
        )
        return

    await OrderDetailedView.change_status.set()
    async with Dispatcher.get_current().current_state().proxy() as data:
        data['order'] = order

    await message.answer(
        text,
        reply_markup=await OrderDetailedViewKeyBoard.get_reply_markup(user),
    )


async def choose_status_order(message: types.Message, user: User, state: FSMContext):
    await OrderDetailedView.next()
    await message.answer(
        f"Выберете статус",
        reply_markup=await OrderChangeStatusKeyBoard.get_reply_markup(user),
    )


async def change_status_order(message: types.Message, user: User, state: FSMContext):
    async with state.proxy() as data:
        order: Order = data['order']
        was = OrderStatus.get_str_by_id(order.status_id)
        new = OrderStatus.get_id_by_str(message.text)
        await order.change_status(new)

        await message.answer(
            f"Статус успешно изменен {was} -> {message.text}",
            reply_markup=await MainMenuKeyBoard.get_reply_markup(user),
        )
    await state.finish()


async def register_handlers(dp: Dispatcher):
    dp.message_handler(
        Text(equals=MainMenuKeyBoard.Button.orders.value),
        AuthorizedUser(return_user=True),
    )(start_order_main_menu)
    dp.message_handler(
        Text(equals=OrderActionKeyBoard.Button.view.value),
        AuthorizedUser(return_user=True),
        state=OrderMain.action,
    )(view_order_type_menu)
    dp.message_handler(
        Text(equals=OrderViewTypeKeyBoard.get_values()),
        AuthorizedUser(return_user=True),
        state=OrderView.type,
    )(view_order_to_menu)
    dp.message_handler(
        Text(equals=OrderViewToKeyBoard.get_values()),
        AuthorizedUser(return_user=True),
        state=OrderView.to,
    )(view_order_show)

    dp.message_handler(
        RegexpCommandsFilter(regexp_commands=[r'order_(\d+)$']),
        AuthorizedUser(return_user=True),
    )(view_single_order)
    dp.message_handler(
        Text(equals=OrderDetailedViewKeyBoard.get_values()),
        AuthorizedUser(return_user=True, user_role=UserRole.ACCOUNTANT),
        state=OrderDetailedView.change_status,
    )(choose_status_order)
    dp.message_handler(
        Text(equals=OrderChangeStatusKeyBoard.get_values()),
        AuthorizedUser(return_user=True, user_role=UserRole.ACCOUNTANT),
        state=OrderDetailedView.status,
    )(change_status_order)
