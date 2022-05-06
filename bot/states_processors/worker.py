import uuid
from typing import Match

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text, RegexpCommandsFilter

from bot.sdk.common import get_order_view, list_documents, list_workers, create_order_by_accountant
from bot.sdk.filters import AuthorizedUser, not_cancel
from bot.sdk.keyboards import MainMenuKeyBoard, WorkerManageActionKeyBoard, WorkerManageAddInvitationRoleKeyBoard, \
    WorkerDetailedViewKeyBoard
from bot.states import (
    WorkerManage,
    WorkerManageAddInvite, WorkerManageDeleteInvite, WorkerManageDeleteWorker, WorkerDetailedView, WorkerAskDocument,
    DocumentAskedByWorker,
)
from database.models import (
    User, UserRole, Invitation, Order, Document,
)


async def manage_start(message: types.Message, user: User):
    await WorkerManage.action.set()

    await message.answer(
        f"Выберете, что сделать",
        reply_markup=await WorkerManageActionKeyBoard.get_reply_markup(user),
    )


async def manage_view_invitation(message: types.Message, state: FSMContext, user: User):
    await state.finish()
    invitation: list[Invitation] = await Invitation.get_all()

    text = 'Приглашения: \n'
    for invite in invitation:
        text += f'{invite.id}. {invite.username} -- {UserRole.get_str_by_id(invite.role_id)}\n\n'
    await message.answer(
        text,
        reply_markup=await MainMenuKeyBoard.get_reply_markup(user),
    )


async def manage_view_worker(message: types.Message, state: FSMContext, user: User):
    await state.finish()
    await list_workers(message, user)


async def manage_add_invitation_begin(message: types.Message, state: FSMContext):
    await state.finish()
    await WorkerManageAddInvite.username.set()
    await message.answer(
        f"Введите ФИО сотрудника",
        reply_markup=types.ReplyKeyboardRemove(),
    )


async def manage_add_invitation_username(message: types.Message, state: FSMContext, user: User):
    if len(message.text) < 3:
        await message.answer(
            f"ФИО слишком короткое. Попробуйте снова",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        return

    async with state.proxy() as data:
        data['username'] = message.text

    await WorkerManageAddInvite.next()
    await message.answer(
        f"Укажите роль",
        reply_markup=await WorkerManageAddInvitationRoleKeyBoard.get_reply_markup(user),
    )


async def manage_add_invitation_role(message: types.Message, state: FSMContext, user: User):
    async with state.proxy() as data:
        data['role_id'] = UserRole.get_id_by_str(message.text)
        data['token'] = str(uuid.uuid4())

        await Invitation.create(**data)
        await message.answer(
            f"Приглашение успешно создано. Попросите сотрудника отправить {data['token']} этому боту",
            reply_markup=await MainMenuKeyBoard.get_reply_markup(user),
        )
        await state.finish()


async def manage_invitation_delete_begin(message: types.Message, state: FSMContext):
    await state.finish()
    await WorkerManageDeleteInvite.action.set()
    await message.answer(
        f"Введите ID приглашения",
        reply_markup=types.ReplyKeyboardRemove(),
    )


async def manage_invitation_delete_action(message: types.Message, state: FSMContext, user: User):
    async with state.proxy() as data:
        try:
            data['id'] = int(message.text)
        except ValueError:
            await message.answer(
                f"Неверный формат ID. Введите число",
                reply_markup=types.ReplyKeyboardRemove(),
            )
            return

        invitation: Invitation = await Invitation.get(id=data['id'])
    await state.finish()
    if not invitation:
        await message.answer(
            f"Приглашение не найдено",
            reply_markup=await MainMenuKeyBoard.get_reply_markup(user),
        )
        return

    await invitation.delete()
    await message.answer(
        f"Приглашение удалено",
        reply_markup=await MainMenuKeyBoard.get_reply_markup(user),
    )


async def manage_worker_delete_begin(message: types.Message, state: FSMContext):
    await state.finish()
    await WorkerManageDeleteWorker.action.set()
    await message.answer(
        f"Введите ID сотрудника",
        reply_markup=types.ReplyKeyboardRemove(),
    )


async def manage_worker_delete_action(message: types.Message, state: FSMContext, user: User):
    async with state.proxy() as data:
        try:
            data['id'] = int(message.text)
        except ValueError:
            await message.answer(
                f"Неверный формат ID. Введите число",
                reply_markup=types.ReplyKeyboardRemove(),
            )
            return

        worker: User = await User.get(id=data['id'], is_deleted=False, role_id=UserRole.WORKER)
    await state.finish()
    if not worker:
        await message.answer(
            f"Рабочий не найден",
            reply_markup=await MainMenuKeyBoard.get_reply_markup(user),
        )
        return

    orders = await Order.get_all_not_completed_order(worker.id)
    if not orders:
        await worker.update(is_deleted=True)
        await message.answer(
            f"Рабочий удален",
            reply_markup=await MainMenuKeyBoard.get_reply_markup(user),
        )
        return

    text = 'У данного работника имеются не завершенные заказы. Измените статус.\n\n'
    text += await get_order_view(orders, user)
    await message.answer(
        text,
        reply_markup=await MainMenuKeyBoard.get_reply_markup(user),
    )
    await state.finish()


async def detailed_view_worker(message: types.Message, regexp_command: Match, user: User):
    worker_id = int(regexp_command.group(1))
    worker: User = await User.get(id=worker_id, is_deleted=False, role_id=UserRole.WORKER)
    if not worker:
        await message.answer(f"Рабочий не найден")
        return

    await WorkerDetailedView.action.set()
    async with Dispatcher.get_current().current_state().proxy() as data:
        data['worker'] = worker

    await message.answer(
        f"Работник: №{worker.id}. {worker.username}\nЧто вы хотите сделать?",
        reply_markup=await WorkerDetailedViewKeyBoard.get_reply_markup(user),
    )


async def ask_for_document_by_accountant(message: types.Message, state: FSMContext, regexp_command: Match, user: User):
    worker_id = int(regexp_command.group(1))
    worker: User = await User.get(id=worker_id, is_deleted=False, role_id=UserRole.WORKER)
    if not worker:
        await message.answer(f"Рабочий не найден")
        return

    async with state.proxy() as data:
        document: Document = data['document']

    await state.finish()
    await create_order_by_accountant(message, user, document, worker)


async def detailed_view_delete_worker(message: types.Message, user: User, state: FSMContext):
    async with state.proxy() as data:
        worker: User = data['worker']
        message.text = worker.id
        await manage_worker_delete_action(message, state, user)


async def detailed_view_order_document_worker(message: types.Message, user: User, state: FSMContext):
    async with state.proxy() as data:
        worker: User = data['worker']

    await state.finish()
    await WorkerAskDocument.document.set()
    async with Dispatcher.get_current().current_state().proxy() as data:
        data['worker'] = worker
    await message.answer("Выберете документ")
    await list_documents(message)


async def register_handlers(dp: Dispatcher):
    dp.message_handler(
        Text(MainMenuKeyBoard.Button.admin_manage_worker.value),
        AuthorizedUser(return_user=True, user_role=UserRole.ACCOUNTANT),
    )(manage_start)

    dp.message_handler(
        Text(WorkerManageActionKeyBoard.Button.add_inv.value),
        AuthorizedUser(user_role=UserRole.ACCOUNTANT),
        state=WorkerManage.action,
    )(manage_add_invitation_begin)
    dp.message_handler(
        not_cancel,
        AuthorizedUser(return_user=True, user_role=UserRole.ACCOUNTANT),
        state=WorkerManageAddInvite.username,
    )(manage_add_invitation_username)
    dp.message_handler(
        Text(equals=WorkerManageAddInvitationRoleKeyBoard.get_values()),
        AuthorizedUser(return_user=True, user_role=UserRole.ACCOUNTANT),
        state=WorkerManageAddInvite.role,
    )(manage_add_invitation_role)

    dp.message_handler(
        Text(WorkerManageActionKeyBoard.Button.view_inv.value),
        AuthorizedUser(user_role=UserRole.ACCOUNTANT, return_user=True),
        state=WorkerManage.action,
    )(manage_view_invitation)

    dp.message_handler(
        Text(WorkerManageActionKeyBoard.Button.view_worker.value),
        AuthorizedUser(user_role=UserRole.ACCOUNTANT, return_user=True),
        state=WorkerManage.action,
    )(manage_view_worker)

    dp.message_handler(
        Text(WorkerManageActionKeyBoard.Button.delete_inv.value),
        AuthorizedUser(user_role=UserRole.ACCOUNTANT),
        state=WorkerManage.action,
    )(manage_invitation_delete_begin)
    dp.message_handler(
        not_cancel,
        AuthorizedUser(user_role=UserRole.ACCOUNTANT, return_user=True),
        state=WorkerManageDeleteInvite.action,
    )(manage_invitation_delete_action)

    dp.message_handler(
        Text(WorkerManageActionKeyBoard.Button.delete_worker.value),
        AuthorizedUser(user_role=UserRole.ACCOUNTANT),
        state=WorkerManage.action,
    )(manage_worker_delete_begin)
    dp.message_handler(
        not_cancel,
        AuthorizedUser(user_role=UserRole.ACCOUNTANT, return_user=True),
        state=WorkerManageDeleteWorker.action,
    )(manage_worker_delete_action)

    dp.message_handler(
        RegexpCommandsFilter(regexp_commands=[r'worker_(\d+)$']),
        AuthorizedUser(return_user=True, user_role=UserRole.ACCOUNTANT),
    )(detailed_view_worker)
    dp.message_handler(
        RegexpCommandsFilter(regexp_commands=[r'worker_(\d+)$']),
        AuthorizedUser(return_user=True, user_role=UserRole.ACCOUNTANT),
        state=DocumentAskedByWorker.action,
    )(ask_for_document_by_accountant)
    dp.message_handler(
        Text(WorkerDetailedViewKeyBoard.Button.delete.value),
        AuthorizedUser(user_role=UserRole.ACCOUNTANT, return_user=True),
        state=WorkerDetailedView.action,
    )(detailed_view_delete_worker)
    dp.message_handler(
        Text(WorkerDetailedViewKeyBoard.Button.orders.value),
        AuthorizedUser(user_role=UserRole.ACCOUNTANT, return_user=True),
        state=WorkerDetailedView.action,
    )(detailed_view_order_document_worker)
