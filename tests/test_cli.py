from hacknews.cli import parse_args


def test_parse_run_args():
    args = parse_args(["run", "morning", "--config", "c.yaml"])
    assert args.command == "run"
    assert args.job == "morning"
    assert args.config == "c.yaml"
