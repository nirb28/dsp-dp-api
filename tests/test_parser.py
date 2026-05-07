import pytest

from app.errors import DataProductError
from app.parser import parse_data_product_yaml


VALID_YAML = """
version: "1.0"
project:
  id: "dp_transaction_scoring_01"
  name: "Transaction Scoring Data Product"
connection:
  type: "postgres"
  properties:
    host: "localhost"
mdl: |
  {"models": [], "relationships": [], "metrics": []}
semantics:
  sql_pairs: |
    [{"question": "q", "sql": "select 1"}]
"""


def test_parse_data_product_yaml_decodes_raw_json_strings():
    parsed = parse_data_product_yaml(VALID_YAML)

    assert parsed.document.project.id == "dp_transaction_scoring_01"
    assert parsed.mdl_json == {"models": [], "relationships": [], "metrics": [], "views": []}
    assert parsed.sql_pairs_json[0].question == "q"


def test_parse_data_product_yaml_normalizes_simplified_mdl_shapes():
    content = VALID_YAML.replace(
        '{"models": [], "relationships": [], "metrics": []}',
        """
        {
          "models": [
            {
              "name": "transactions",
              "tableReference": "fact_transactions",
              "columns": [{"name": "transaction_id", "type": "integer", "primaryKey": true}]
            }
          ],
          "relationships": [{"name": "r", "from": "transactions", "to": "customers", "joinType": "many_to_one"}],
          "metrics": [{"name": "m", "model": "transactions", "measure": "avg(score)"}]
        }
        """,
    )

    parsed = parse_data_product_yaml(content)

    assert parsed.mdl_json["models"][0]["tableReference"] == {"table": "fact_transactions"}
    assert parsed.mdl_json["models"][0]["primaryKey"] == "transaction_id"
    assert parsed.mdl_json["relationships"][0]["models"] == ["transactions", "customers"]
    assert parsed.mdl_json["relationships"][0]["joinType"] == "MANY_TO_ONE"
    assert parsed.mdl_json["metrics"][0]["baseObject"] == "transactions"
    assert parsed.mdl_json["metrics"][0]["measure"][0]["expression"] == "avg(score)"
    assert parsed.mdl_json["metrics"][0]["timeGrain"] == []


def test_parse_data_product_yaml_rejects_invalid_mdl_json():
    content = VALID_YAML.replace('{"models": [], "relationships": [], "metrics": []}', "not-json")

    with pytest.raises(DataProductError, match="mdl must be a valid raw JSON string"):
        parse_data_product_yaml(content)


def test_parse_data_product_yaml_rejects_non_array_sql_pairs():
    content = VALID_YAML.replace('[{"question": "q", "sql": "select 1"}]', "{\"question\": \"q\"}")

    with pytest.raises(DataProductError, match="semantics.sql_pairs must decode to a JSON array"):
        parse_data_product_yaml(content)
