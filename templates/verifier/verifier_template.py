# verifier_template.py
#
# Copy this file into an environment package under src/<package>/verifiers/
# and rename appropriately. Fill in implementation details and tests.

from __future__ import annotations

from typing import Any, Mapping

from ..interfaces import Verifier


class MyVerifier(Verifier):
    """Template verifier.

    Replace this docstring with a concise description of the scoring policy.
    """

    def __init__(self) -> None:
        self._last: dict[str, Any] = {}

    def score(self, input_text: str, output_text: str) -> float:
        # TODO: implement scoring logic
        self._last = {"note": "unimplemented"}
        raise NotImplementedError

    def details(self) -> Mapping[str, Any]:
        return self._last
