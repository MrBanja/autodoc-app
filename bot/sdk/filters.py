from aiogram import types
from aiogram.dispatcher.filters import Filter

from database.models import User


class AuthorizedUser(Filter):

    def __init__(self, user_role: int | None = None, return_user: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_role = user_role
        self.return_user = return_user

    async def check(self, obj: types.Message | types.CallbackQuery | types.InlineQuery | types.Poll):
        user = await User.get_by_telegram_id(obj.from_user.id)
        if not user:
            return False
        if self.user_role is not None and user.role_id != self.user_role:
            return False

        if self.return_user:
            return dict(user=user)
        return True


def not_cancel(message: types.Message) -> bool:
    if message.text == 'Отмена' or message.text == '/cancel':
        return False
    return True
