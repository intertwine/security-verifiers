from sv_env_config_verification.e2_config_auditing.adapters.types import Violation
from sv_env_config_verification.e2_config_auditing.reward import final_reward, score_detection


def test_score_detection() -> None:
    oracle = [Violation(id="a", severity="high")]
    pred = [Violation(id="a", severity="high")]
    p, r, f1 = score_detection(pred, oracle)
    assert p == r == f1 == 1.0


def test_final_reward_patch_delta() -> None:
    oracle = [Violation(id="a", severity="high")]
    pred: list[Violation] = []
    post: list[Violation] = []
    reward = final_reward(pred, oracle, post_patch=post)
    assert reward > 1.0  # format bonus + patch removal
