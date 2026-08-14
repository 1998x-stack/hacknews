import json

from hacknews.logging_setup import get_logger, setup_logging


def test_json_logger_writes_structured_record(capsys):
    setup_logging("INFO", job="j1")
    log = get_logger("test")
    log.info("hello", extra={"event": "x"})
    out = capsys.readouterr().out.strip()
    record = json.loads(out.splitlines()[-1])
    assert record["level"] == "INFO"
    assert record["event"] == "x"
    assert record["job"] == "j1"
    assert "ts" in record
