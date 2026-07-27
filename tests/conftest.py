import pytest
from sqlalchemy import create_engine

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

    Base.metadata.create_all(e)

    yield e

    Base.metadata.drop_all(e)

    e.dispose()
