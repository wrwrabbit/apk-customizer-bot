from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

IGNORED_BAD_REQUEST_MESSAGES = (
    "message to delete not found",
    "message can't be deleted",
    "message to edit not found",
    "message is not modified",
    "message to reply not found",
    "MESSAGE_ID_INVALID",
    "query is too old and response timeout expired or query id is invalid",
)


def is_ignorable_telegram_error(exception: BaseException) -> bool:
    if isinstance(exception, TelegramForbiddenError):
        return True
    if isinstance(exception, TelegramBadRequest):
        message = exception.message.lower()
        return any(ignored.lower() in message for ignored in IGNORED_BAD_REQUEST_MESSAGES)
    return False
