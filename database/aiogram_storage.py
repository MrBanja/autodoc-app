import aio_pika
from aiogram.contrib.fsm_storage.memory import MemoryStorage

storage = MemoryStorage()


def get_channel() -> aio_pika.channel.Channel:
    return storage.data['rmq_channel']['channel']
