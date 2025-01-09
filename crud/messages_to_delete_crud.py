from datetime import datetime
from typing import Optional, Iterator

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.message_to_delete import MessageToDelete


class MessagesToDeleteCRUD:
    def __init__(self, session: Session):
        self.session = session

    def add_message_to_delete(self, message_to_delete: MessageToDelete):
        try:
            self.session.execute(
                sa.insert(MessageToDelete)
                .values(
                    {
                        MessageToDelete.user_id: message_to_delete.user_id,
                        MessageToDelete.message_id: message_to_delete.message_id,
                        MessageToDelete.sent_date: message_to_delete.sent_date,
                    }
                )
            )
        except IntegrityError:
            pass

    def get_count_of_users(self) -> int:
        q = sa.select([sa.func.count(sa.func.distinct(MessageToDelete.user_id))])
        return self.session.execute(q).scalar()

    def get_users(self) -> Iterator[int]:
        q = sa.select([sa.func.distinct(MessageToDelete.user_id)])
        for row in self.session.execute(q).fetchall():
            yield row[0]

    def get_user_messages(self, user_id: int, max_sent_date: Optional[datetime] = None) -> Iterator[MessageToDelete]:
        q = (sa.select(*MessageToDelete.__table__.c)
             .where(MessageToDelete.user_id == user_id))

        if max_sent_date is not None:
            q = q.where(MessageToDelete.sent_date <= max_sent_date)

        records = self.session.execute(q).fetchall()

        for record in records:
            yield MessageToDelete(**record)

    def get_user_messages_count(self, user_id: int) -> int:
        q = (sa.select([sa.func.count(MessageToDelete.message_id)])
             .where(MessageToDelete.user_id == user_id))
        return self.session.execute(q).scalar()

    def remove_user_messages(self, user_id: int, max_sent_date: Optional[datetime] = None):
        q = sa.delete(MessageToDelete).where(MessageToDelete.user_id == user_id)
        if max_sent_date is not None:
            q = q.where(MessageToDelete.sent_date <= max_sent_date)
        self.session.execute(q)

    def remove_message(self, user_id: int, message_id: int):
        self.session.execute(sa.delete(MessageToDelete).where((MessageToDelete.user_id == user_id) & (MessageToDelete.message_id == message_id)))
