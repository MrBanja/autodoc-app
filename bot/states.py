from aiogram.dispatcher.filters.state import State, StatesGroup


class FirstInvitation(StatesGroup):
    token_enter = State()


class DocumentView(StatesGroup):
    action = State()


class DocumentManageView(StatesGroup):
    action = State()


class DocumentManageAddView(StatesGroup):
    document_name = State()


class DocumentManageDeleteView(StatesGroup):
    document_name = State()


class OrderMain(StatesGroup):
    action = State()


class OrderView(StatesGroup):
    type = State()
    to = State()


class OrderDetailedView(StatesGroup):
    change_status = State()
    status = State()


class WorkerManage(StatesGroup):
    action = State()


class WorkerManageAddInvite(StatesGroup):
    username = State()
    role = State()


class WorkerManageDeleteInvite(StatesGroup):
    action = State()


class WorkerManageDeleteWorker(StatesGroup):
    action = State()


class WorkerDetailedView(StatesGroup):
    action = State()


class WorkerAskDocument(StatesGroup):
    document = State()


class DocumentAskedByWorker(StatesGroup):
    action = State()
