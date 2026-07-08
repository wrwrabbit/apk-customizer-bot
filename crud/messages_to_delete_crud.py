from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert

from crud.base_crud import BaseCRUD
from models.message_to_delete import MessageToDelete


class MessagesToDeleteCRUD(BaseCRUD):
    def add_message_to_delete(self, message_to_delete: MessageToDelete):
        q = (
            pg_insert(MessageToDelete)
            .values(
                user_id=message_to_delete.user_id,
                message_id=message_to_delete.message_id,
                sent_date=message_to_delete.sent_date,
            )
            .on_conflict_do_nothing(index_elements=[MessageToDelete.user_id, MessageToDelete.message_id])
        )
        with self._session_factory.begin() as session:
            session.execute(q)

    def get_count_of_users(self) -> int:
        q = sa.select(sa.func.count(sa.func.distinct(MessageToDelete.user_id)))
        with self._session_factory() as session:
            return session.scalar(q)

    def get_users(self) -> list[int]:
        q = sa.select(sa.func.distinct(MessageToDelete.user_id))
        with self._session_factory() as session:
            return list(session.scalars(q))

    def get_user_messages(self, user_id: int, max_sent_date: Optional[datetime] = None) -> list[MessageToDelete]:
        q = (sa.select(MessageToDelete)
             .where(MessageToDelete.user_id == user_id))

        if max_sent_date is not None:
            q = q.where(MessageToDelete.sent_date <= max_sent_date)

        with self._session_factory() as session:
            return list(session.scalars(q))

    def get_user_messages_count(self, user_id: int) -> int:
        q = (sa.select(sa.func.count(MessageToDelete.message_id))
             .where(MessageToDelete.user_id == user_id))
        with self._session_factory() as session:
            return session.scalar(q)

    def remove_user_messages(self, user_id: int, max_sent_date: Optional[datetime] = None):
        q = sa.delete(MessageToDelete).where(MessageToDelete.user_id == user_id)
        if max_sent_date is not None:
            q = q.where(MessageToDelete.sent_date <= max_sent_date)
        with self._session_factory.begin() as session:
            session.execute(q)

    def remove_message(self, user_id: int, message_id: int):
        with self._session_factory.begin() as session:
            session.execute(sa.delete(MessageToDelete).where((MessageToDelete.user_id == user_id) & (MessageToDelete.message_id == message_id)))
