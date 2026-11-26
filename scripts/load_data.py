"""Olist CSV를 내려받아 PostgreSQL에 적재하는 스크립트."""

import os
from pathlib import Path

import kagglehub
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, text

DATASET = "olistbr/brazilian-ecommerce/versions/2"


def download_dataset() -> Path:
    """Kaggle에서 데이터셋을 내려받고 CSV가 있는 폴더 경로를 돌려준다."""
    path = kagglehub.dataset_download(DATASET)
    return Path(path)


def check_db_connection(engine: Engine) -> str:
    """DB에 접속해 PostgreSQL 버전 문자열을 돌려준다."""

    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.scalar()
    return version


def to_table_name(csv_path: Path) -> str:
    """csv 파일 이름을 테이블 이름으로 바꾼다."""
    name = csv_path.stem

    name = name.removeprefix("olist_")
    name = name.removesuffix("_dataset")
    return name


def is_date_column(column: str) -> bool:
    """컬럼 이름으로 날짜 컬럼인지 판단한다."""
    return "date" in column or "timestamp" in column or column.endswith("_at")


def load_csv(csv_path: Path, table_name: str, engine: Engine) -> int:
    """CSV 하나를 읽어 테이블로 저장하고, 읽은 행 수를 돌려준다."""
    df = pd.read_csv(csv_path)

    for column in df.columns:
        if is_date_column(column):
            df[column] = pd.to_datetime(df[column])

    df.to_sql(table_name, engine, if_exists="replace", index=False, chunksize=10_000)
    return len(df)


def count_rows(engine: Engine, table_name: str) -> int:
    """DB 테이블의 행 수를 센다."""
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return result.scalar()


def main() -> None:
    """Olist CSV 9개를 PostgreSQL 테이블로 적재하고 행 수를 검증한다."""
    load_dotenv()
    engine = create_engine(os.environ["DATABASE_URL"])
    print("DB 버전:", check_db_connection(engine))

    data_dir = download_dataset()
    csv_paths = sorted(data_dir.glob("*.csv"))
    print("CSV 파일 수:", len(csv_paths))

    for csv_path in csv_paths:
        table_name = to_table_name(csv_path)
        csv_rows = load_csv(csv_path, table_name, engine)
        db_rows = count_rows(engine, table_name)

        if csv_rows == db_rows:
            status = "OK"
        else:
            status = "불일치"
        print(f"{table_name}: csv {csv_rows}행 / DB {db_rows}행 -> {status}")


if __name__ == "__main__":
    main()
