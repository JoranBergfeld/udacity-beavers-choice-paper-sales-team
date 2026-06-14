import pytest
from pydantic_ai.models.test import TestModel

from backend.munder.eval.judge import JudgeScores, build_judge, judge_text


def test_judge_scores_model_bounds():
    s = JudgeScores(clarity=4, transparency=5, personality=3,
                    persuasiveness=4, rationale="ok")
    assert 1 <= s.clarity <= 5


@pytest.mark.asyncio
async def test_judge_text_returns_scores_with_testmodel():
    judge = build_judge(model=TestModel())
    scores = await judge_text(judge, agent_name="Jim",
                              output_text="10% bulk discount applied, total $24.50.")
    assert isinstance(scores, JudgeScores)
