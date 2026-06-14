from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models import Model

from backend.munder.agents import build_model


class JudgeScores(BaseModel):
    clarity: int = Field(ge=1, le=5)
    transparency: int = Field(ge=1, le=5)
    personality: int = Field(ge=1, le=5)
    persuasiveness: int = Field(ge=1, le=5)
    rationale: str


_JUDGE_PROMPT = (
    "You are an impartial evaluator of a customer-service agent's output. Score 1-5 on "
    "clarity, transparency (rationale present, no internal info leaked), personality "
    "(fits the named Office character), and persuasiveness. Give a one-sentence rationale."
)


def build_judge(model: Optional[Model] = None) -> Agent:
    return Agent(model or build_model(), output_type=JudgeScores,
                 system_prompt=_JUDGE_PROMPT)


async def judge_text(judge: Agent, agent_name: str, output_text: str) -> JudgeScores:
    prompt = f"Agent: {agent_name}\nOutput:\n{output_text}"
    return (await judge.run(prompt)).output
