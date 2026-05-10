import json
import os
from pathlib import Path

import yaml
from trino.auth import BasicAuthentication
from trino.dbapi import connect

HOST = "daljeetsm-free-cluster.trino.galaxy.starburst.io"
IBIS_HOST = f"https://{HOST}"
PORT = 443
CATALOG = "sample"
SCHEMA = "burstbank"
PROJECT_ID = "dp_starburst_burstbank_01"

TYPE_MAP = {
    "bigint": "integer",
    "integer": "integer",
    "smallint": "integer",
    "tinyint": "integer",
    "double": "double",
    "real": "float",
    "decimal": "decimal",
    "varchar": "varchar",
    "char": "varchar",
    "boolean": "boolean",
    "date": "date",
    "timestamp": "timestamp",
    "timestamp with time zone": "timestamp",
    "time": "time",
    "time with time zone": "time",
}


def main() -> None:
    _load_env_file(Path(__file__).resolve().parents[2] / ".env")
    username = os.environ["STARBURST_USERNAME"]
    password = os.environ["STARBURST_PASSWORD"]
    output_path = Path(os.environ.get("OUTPUT_PATH", "examples/starburst/burstbank_data_product.yaml"))

    conn = connect(
        host=HOST,
        port=PORT,
        user=username,
        catalog=CATALOG,
        schema=SCHEMA,
        http_scheme="https",
        auth=BasicAuthentication(username, password),
    )

    with conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_catalog = '{_sql_literal(CATALOG)}'
              AND table_schema = '{_sql_literal(SCHEMA)}'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )
        table_names = [row[0] for row in cursor.fetchall()]

        models = []
        for table_name in table_names:
            cursor.execute(
                f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_catalog = '{_sql_literal(CATALOG)}'
                  AND table_schema = '{_sql_literal(SCHEMA)}'
                  AND table_name = '{_sql_literal(table_name)}'
                ORDER BY ordinal_position
                """
            )
            columns = [
                {
                    "name": column_name,
                    "type": _map_type(column_name, data_type),
                }
                for column_name, data_type in cursor.fetchall()
            ]
            models.append(
                {
                    "name": table_name,
                    "tableReference": {
                        "catalog": CATALOG,
                        "schema": SCHEMA,
                        "table": table_name,
                    },
                    "description": f"Starburst table {CATALOG}.{SCHEMA}.{table_name}",
                    "columns": columns,
                }
            )

    data_product = {
        "version": "1.0",
        "project": {
            "id": PROJECT_ID,
            "name": "Starburst Burstbank Data Product",
            "description": "Data product generated from Starburst Cloud sample.burstbank.",
        },
        "connection": {
            "type": "trino",
            "properties": {
                "host": IBIS_HOST,
                "port": str(PORT),
                "catalog": CATALOG,
                "schema": SCHEMA,
                "user": "${STARBURST_USERNAME}",
                "password": "${STARBURST_PASSWORD}",
            },
        },
        "mdl": json.dumps(
            {
                "catalog": CATALOG,
                "schema": SCHEMA,
                "dataSource": "trino",
                "models": models,
                "relationships": [],
                "metrics": [],
                "views": [],
            },
            indent=2,
        ),
        "semantics": {
            "sql_pairs": json.dumps([], indent=2),
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml.safe_dump(data_product, sort_keys=False), encoding="utf-8")
    print(output_path)


def _map_type(column_name: str, data_type: str) -> str:
    if column_name.lower().endswith("_date") or column_name.lower() in {"date", "dob"}:
        return "date"
    normalized = data_type.lower().split("(", 1)[0].strip()
    return TYPE_MAP.get(normalized, "varchar")


def _sql_literal(value: str) -> str:
    return value.replace("'", "''")


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


if __name__ == "__main__":
    main()
