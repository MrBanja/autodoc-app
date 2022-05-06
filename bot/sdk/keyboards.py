import abc
import enum

from aiogram import types

from database.models import User, UserRole
from utils.functions import get_all_enum_values


class ExtraButtons(str, enum.Enum):
    cancel = 'Отмена'


class AbstractKeyBoard(metaclass=abc.ABCMeta):

    class Button(str, enum.Enum):
        pass

    extra_buttons: set[enum.Enum] = {ExtraButtons.cancel}
    accountant_buttons: set[enum.Enum] = set()

    @classmethod
    def get_values(cls) -> list[str]:
        return get_all_enum_values(cls.Button)

    @classmethod
    async def get_reply_markup(cls, user: User, *args, **kwargs) -> types.ReplyKeyboardMarkup:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)

        exclude_set = None
        extra_set = {c.value for c in cls.extra_buttons}
        if user.role_id != UserRole.ACCOUNTANT:
            exclude_set = {c.value for c in cls.accountant_buttons}

        markup.add(*get_all_enum_values(cls.Button, except_values=exclude_set, extra_values=extra_set))
        return markup


class MainMenuKeyBoard(AbstractKeyBoard):

    class Button(str, enum.Enum):
        doc_list = "📄Список документов"
        orders = "✍︎Заявки"

        admin_manage_doc = "⚙️Управление документами"
        admin_manage_worker = "👷Управление рабочими"

    extra_buttons: set[enum.Enum] = set()
    accountant_buttons: set[enum.Enum] = {Button.admin_manage_worker, Button.admin_manage_doc}


class WorkerDetailedViewKeyBoard(AbstractKeyBoard):

    class Button(str, enum.Enum):
        delete = "🗑Удалить"
        orders = "📄Запросить документ"


class DocumentActionKeyBoard(AbstractKeyBoard):

    class Button(str, enum.Enum):
        ask = "📄Запросить"

        admin_delete = "🗑Удалить"

    accountant_buttons: set[enum.Enum] = {Button.admin_delete}


class DocumentManageActionKeyBoard(AbstractKeyBoard):

    class Button(str, enum.Enum):
        add = "➕Добавить"
        delete = "🗑Удалить"


class WorkerManageActionKeyBoard(AbstractKeyBoard):

    class Button(str, enum.Enum):
        add_inv = "➕Добавить приглашение"
        delete_inv = "🗑Удалить приглашение"
        view_inv = "👥‍Просмотреть список приглашений"
        delete_worker = "🙅Удалить сотрудника"
        view_worker = "👥‍Просмотреть список сотрудника"


class WorkerManageAddInvitationRoleKeyBoard(AbstractKeyBoard):

    class Button(str, enum.Enum):
        accountant = "🧑‍💻Бухгалтер"
        worker = "👷‍Сотрудник"


class OrderActionKeyBoard(AbstractKeyBoard):

    class Button(str, enum.Enum):
        view = "Просмотреть список заявок"


class OrderViewTypeKeyBoard(AbstractKeyBoard):

    class Button(str, enum.Enum):
        new = "Активные"
        old = "Завершенные"
        all = "Все"


class OrderViewToKeyBoard(AbstractKeyBoard):

    class Button(str, enum.Enum):
        to_me = "Я запрашивал"
        from_me = "Запрашивали у меня"


class OrderDetailedViewKeyBoard(AbstractKeyBoard):

    class Button(str, enum.Enum):
        change_status = "Сменить статус"


class OrderChangeStatusKeyBoard(AbstractKeyBoard):

    class Button(str, enum.Enum):
        new = 'Новая'
        processing = 'Обрабатывается'
        ready = 'Готова к выдачи'
        done = 'Выполнена'
        declined = 'Отменена'
