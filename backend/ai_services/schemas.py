from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class MaterialAnalysis(StrictModel):
    summary: str = Field(min_length=1, max_length=6000)
    topics: list[str] = Field(max_length=30)
    concepts: list[str] = Field(max_length=50)
    objectives: list[str] = Field(max_length=30)
    terminology: list[str] = Field(max_length=50)


class GeneratedTest(StrictModel):
    input: str = Field(max_length=10000)
    expected_output: str = Field(max_length=10000)
    is_hidden: bool
    weight: int = Field(default=1, ge=1, le=100)


class GeneratedQuestion(StrictModel):
    type: Literal['mcq','multiple_select','fill_blank','short_answer','descriptive','coding','debugging','output_prediction','scenario','genai_practical','project']
    title: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=12000)
    difficulty: Literal['easy','medium','hard']
    marks: float = Field(gt=0, le=10000)
    options: list[str] = Field(default_factory=list, max_length=20)
    correct_answer: list[str] = Field(default_factory=list, max_length=20)
    explanation: str = Field(default='', max_length=5000)
    rubric: str = Field(default='', max_length=5000)
    marking_policy: Literal['exact','partial'] = 'exact'
    constraints: str = Field(default='', max_length=3000)
    input_format: str = Field(default='', max_length=3000)
    output_format: str = Field(default='', max_length=3000)
    starter_code: str = Field(default='', max_length=10000)
    language: Literal['python'] = 'python'
    test_cases: list[GeneratedTest] = Field(default_factory=list, max_length=20)


class GeneratedAssignment(StrictModel):
    description: str = Field(max_length=6000)
    questions: list[GeneratedQuestion] = Field(min_length=1, max_length=10)

    @model_validator(mode='after')
    def validate_questions(self):
        from assignments.serializers import QuestionSerializer
        from rest_framework.exceptions import ValidationError
        titles = [q.title.strip().lower() for q in self.questions]
        if len(titles) != len(set(titles)):
            raise ValueError('Duplicate question titles.')
        try:
            serializer = QuestionSerializer(data=[q.model_dump() for q in self.questions], many=True)
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            raise ValueError('Invalid question answers, rubrics, or coding tests.')
        return self


class Recommendation(StrictModel):
    topic_id: int
    assignment_ids: list[int] = Field(default_factory=list, max_length=10)
    reason: str = Field(max_length=1500)
    steps: list[str] = Field(max_length=8)
    difficulty: Literal['easy','medium','hard']


class ReportNarrative(StrictModel):
    overall_performance: str = Field(min_length=1, max_length=3000)
    strengths: list[str] = Field(max_length=12)
    weaknesses: list[str] = Field(max_length=12)
    coding_analysis: str = Field(max_length=3000)
    progress_analysis: str = Field(max_length=3000)
    recommendations: list[Recommendation] = Field(max_length=12)
    trainer_feedback: str = Field(max_length=3000)
    evidence_submission_ids: list[int] = Field(max_length=100)


class EvaluationSuggestion(StrictModel):
    rubric_feedback: str = Field(max_length=4000)
    strengths: list[str] = Field(max_length=10)
    gaps: list[str] = Field(max_length=10)


class Explanation(StrictModel):
    explanation: str = Field(min_length=1, max_length=4000)


class BatchNarrative(StrictModel):
    overview: str = Field(min_length=1, max_length=3000)
    strengths: list[str] = Field(max_length=12)
    learning_gaps: list[str] = Field(max_length=12)
    teaching_recommendations: list[str] = Field(max_length=12)
    priority_topic_ids: list[int] = Field(max_length=20)
