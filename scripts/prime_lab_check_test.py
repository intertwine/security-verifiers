from prime_lab_check import has_subcommand


def test_has_subcommand_matches_top_level_command() -> None:
    help_text = """
Usage: prime [OPTIONS] COMMAND [ARGS]...

Commands:
  env   Manage environments
  lab   Hosted training and evaluation
"""
    assert has_subcommand(help_text, "lab")


def test_has_subcommand_false_when_missing() -> None:
    help_text = """
Usage: prime [OPTIONS] COMMAND [ARGS]...

Commands:
  env   Manage environments
"""
    assert not has_subcommand(help_text, "lab")
