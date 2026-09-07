from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app import database


def test_init_db_adds_missing_recommendation_columns(tmp_path, monkeypatch):
    db_path = tmp_path / "farmoptima_test.db"
    test_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    with test_engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE recommendations (
                    id INTEGER PRIMARY KEY,
                    farm_id INTEGER,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    ndvi REAL,
                    soil_ph REAL,
                    top_crop TEXT,
                    full_result TEXT,
                    created_at DATETIME
                )
                """
            )
        )

    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "SessionLocal", TestSessionLocal)

    database.init_db()

    with test_engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(recommendations)"))}

    assert "ndvi_status" in cols
    assert "satellite_scene_date" in cols
