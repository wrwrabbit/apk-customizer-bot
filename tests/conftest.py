import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import config
from models import Base

db_url = (
    f"postgresql://"
    f"{config.DATABASE_USER}:"
    f"{config.DATABASE_PASSWORD}@"
    f"{config.DATABASE_HOST}:"
    f"{config.DATABASE_PORT}/"
    f"test"
)


@pytest.fixture(scope="function")
def engine():
    e = create_engine(
        db_url,
        echo=False,
    )

    with e.connect() as s:
        Base.metadata.create_all(s)

    yield e

    with e.connect() as s:
        Base.metadata.drop_all(s)

    e.dispose()


@pytest.fixture(scope="function")
def session(engine):
    with Session(engine) as s:
        yield s
