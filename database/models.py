from datetime import datetime
from typing import Optional

import sqlalchemy as sa

from database.aiogram_storage import get_channel
from database.controller import DbController
from database.db_core import Base
from utils.rabbit import queue_push
from utils.types import (
    IntColumnType,
    StrColumnType,
    BoolColumnType,
    DateTimeColumnType,
)


class UserRole(Base, DbController):
    __tablename__ = 'user_roles'

    ACCOUNTANT = 1
    WORKER = 2
    SERVICE = 3

    id: IntColumnType = sa.Column(sa.Integer(), primary_key=True)
    name: StrColumnType = sa.Column(sa.String, nullable=False, unique=True)

    @staticmethod
    def get_id_by_str(role: str) -> int | None:
        return {
            "👷‍Сотрудник": UserRole.WORKER,
            "🧑‍💻Бухгалтер": UserRole.ACCOUNTANT,
        }.get(role)

    @staticmethod
    def get_str_by_id(role_id: int) -> str | None:
        return {
            UserRole.WORKER: "👷‍Сотрудник",
            UserRole.ACCOUNTANT: "🧑‍💻Бухгалтер",
        }.get(role_id)


class User(Base, DbController):
    __tablename__ = 'users'

    id: IntColumnType = sa.Column(sa.Integer(), primary_key=True)
    telegram_id: IntColumnType = sa.Column(sa.Integer(), nullable=False, unique=True)
    username: StrColumnType = sa.Column(sa.String(), nullable=False)
    role_id: IntColumnType = sa.Column(sa.Integer(), sa.ForeignKey(UserRole.id), nullable=False)
    is_deleted: BoolColumnType = sa.Column(sa.Boolean(), nullable=False, default=False)

    @staticmethod
    async def get_by_telegram_id(telegram_user_id: int) -> Optional['User']:
        return await User.get(telegram_id=telegram_user_id, is_deleted=False)


class Invitation(Base, DbController):
    __tablename__ = 'invitations'

    id: IntColumnType = sa.Column(sa.Integer(), primary_key=True)
    username: StrColumnType = sa.Column(sa.String(), nullable=False)
    role_id: IntColumnType = sa.Column(sa.Integer(), sa.ForeignKey(UserRole.id), nullable=False)
    token: StrColumnType = sa.Column(sa.String(), nullable=False)

    @staticmethod
    async def get_by_token(token: str) -> Optional['Invitation']:
        return await Invitation.get(custom_filter=Invitation.token == token)


class Document(Base, DbController):
    __tablename__ = 'documents'

    id: IntColumnType = sa.Column(sa.Integer(), primary_key=True)
    name: StrColumnType = sa.Column(sa.String(), nullable=False, unique=True)
    is_deleted: BoolColumnType = sa.Column(sa.Boolean(), nullable=False, default=False)


class OrderStatus(Base, DbController):
    __tablename__ = 'order_statuses'

    NEW = 1
    PROCESSING = 2
    READY = 3
    DONE = 4
    DECLINED = 5

    id: IntColumnType = sa.Column(sa.Integer(), primary_key=True)
    name: StrColumnType = sa.Column(sa.String, nullable=False, unique=True)

    @staticmethod
    def get_str_by_id(order_id: int) -> str | None:
        return {
            1: 'Новая',
            2: 'Обрабатывается',
            3: 'Готова к выдачи',
            4: 'Выполнена',
            5: 'Отменена',
        }.get(order_id)

    @staticmethod
    def get_id_by_str(order: str) -> int | None:
        return {
            'Новая': 1,
            'Обрабатывается': 2,
            'Готова к выдачи': 3,
            'Выполнена': 4,
            'Отменена': 5,
        }.get(order)


class Order(Base, DbController):
    __tablename__ = 'orders'

    id: IntColumnType = sa.Column(sa.Integer(), primary_key=True)
    document_id: IntColumnType = sa.Column(sa.Integer(), sa.ForeignKey(Document.id), nullable=False)
    sender_id: IntColumnType = sa.Column(sa.Integer(), sa.ForeignKey(User.id), nullable=False)
    receiver_id: IntColumnType = sa.Column(sa.Integer(), sa.ForeignKey(User.id), nullable=False)
    status_id: int | sa.Column = sa.Column(sa.Integer(), sa.ForeignKey(OrderStatus.id), nullable=False)
    created_at: DateTimeColumnType = sa.Column(sa.DateTime(), default=datetime.now, nullable=False)
    status_changed_at: DateTimeColumnType = sa.Column(sa.DateTime())
    waiting_for_at: DateTimeColumnType = sa.Column(sa.DateTime())  # Not using it for now

    @staticmethod
    async def create_with_push(
            sender_id: int,
            receiver_id: int,
            document_id: int,
    ) -> 'Order':
        sender: User = await User.get(id=sender_id)
        order: Order = await Order.create(
            sender_id=sender_id,
            document_id=document_id,
            receiver_id=receiver_id,
            status_id=OrderStatus.NEW,
        )
        channel = get_channel()
        await queue_push(
            channel,
            f"У вас запросили документ. Посмотреть заявку можно нажав на\n/order_{order.id}",
            telegram_user_id=sender.telegram_id,
        )
        return order

    @staticmethod
    async def get_not_completed_order(
            document_id: int,
            receiver_id: int | None = None,
            sender_id: int | None = None,
    ) -> Optional['Order']:
        order = await Order.get(custom_filter=sa.and_(
            Order.document_id == document_id,
            Order.receiver_id == receiver_id if receiver_id else True,
            Order.sender_id == sender_id if sender_id else True,
            ~Order.status_id.in_((OrderStatus.DONE, OrderStatus.DECLINED)),
        ))
        return order

    @staticmethod
    async def get_all_not_completed_order(user_id: int) -> list['Order']:
        order = await Order.get_list(custom_filter=sa.and_(
            sa.or_(
                Order.receiver_id == user_id,
                Order.sender_id == user_id
            ),
            ~Order.status_id.in_((OrderStatus.DONE, OrderStatus.DECLINED)),
        ))
        return order

    @staticmethod
    async def get_list_for_view(
            statuses: tuple[int, ...] | None = None,
            receiver_id: int | None = None,
            sender_id: int | None = None,
            document_id: int | None = None,
    ) -> list['Order']:
        return await Order.get_list(custom_filter=sa.and_(
            Order.status_id.in_(statuses) if statuses else True,
            Order.receiver_id == receiver_id if receiver_id else True,
            Order.sender_id == sender_id if sender_id else True,
            Order.document_id == document_id if document_id else True,
        ))

    async def change_status(self, status_id: int):
        receiver: User = await User.get(id=self.receiver_id)
        sender: User = await User.get(id=self.sender_id)
        channel = get_channel()
        message = f'Статус заявки №{self.id} изменен на {OrderStatus.get_str_by_id(status_id)}'
        await queue_push(
            channel,
            message=message,
            telegram_user_id=receiver.telegram_id,
        )
        await queue_push(
            channel,
            message=message,
            telegram_user_id=sender.telegram_id,
        )
        await self.update(
            status_id=status_id,
            status_changed_at=datetime.now(),
        )


class Cell(Base, DbController):
    __tablename__ = 'cells'

    id: IntColumnType = sa.Column(sa.Integer(), primary_key=True)
    order_id: IntColumnType = sa.Column(sa.Integer(), sa.ForeignKey(Order.id))
    is_open: BoolColumnType = sa.Column(sa.Boolean(), nullable=False, default=False)
