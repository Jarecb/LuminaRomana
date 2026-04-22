"""Prompt construction utilities for AI lesson generation.

Defines SystemPromptBuilder, LessonPromptBuilder, and PromptBuilder to assemble
system and user messages used when requesting JSON-formatted lessons from AI
providers.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.ai.types import AIMessage, LessonGenerationRequest, PromptContext, PromptPackage
from app.models import QuestionType, TopicMetadata
from app.services.difficulty import DifficultyAssessment, PromptConstraints


@dataclass(slots=True)
class SystemPromptBuilder:
    def build(self, context: PromptContext) -> str:
        focus_tags = ", ".join(context.focus_tags) if context.focus_tags else "none"
        blocked_topics = ", ".join(context.blocked_topics) if context.blocked_topics else "none"
        return (
            "You are generating Romanian lesson content for English-speaking learners. "
            f"The mandatory grammar topic is '{context.topic_id}' at roadmap level {context.level}. "
            f"The target CEFR band is {context.cefr_band.value} and the target difficulty is {context.difficulty}/10. "
            f"The session goal is '{context.session_goal}'. "
            "Return valid JSON only with no markdown fences or commentary. "
            "Use realistic daily-life contexts, concise explanations, and sensible unambiguous questions. "
            "Avoid archaic, poetic, absurd, or off-topic language. "
            "Questions must stay within the requested topic boundaries unless integrated practice is explicitly justified by learner level and prerequisites. "
            f"Preferred remediation tags: {focus_tags}. "
            f"Do not introduce blocked topics: {blocked_topics}. "
            "Every required field must be present, question tags must stay in scope, and closed-form answers must be internally consistent."
        )


@dataclass(slots=True)
class LessonPromptBuilder:
    def build(
        self,
        request: LessonGenerationRequest,
        topic: TopicMetadata,
        assessment: DifficultyAssessment,
        constraints: PromptConstraints,
    ) -> str:
        prerequisite_text = ", ".join(topic.prerequisites) if topic.prerequisites else "none"
        focus_tags = ", ".join(request.focus_tags) if request.focus_tags else "none"
        blocked_topics = ", ".join(constraints.blocked_topics) if constraints.blocked_topics else "none"
        recent_scores = ", ".join(f"{score:.1f}" for score in request.user_progress.recent_scores) or "none"
        validation_feedback = "; ".join(request.validation_feedback) if request.validation_feedback else "none"
        avoid_question_prompts = " | ".join(request.avoid_question_prompts) if request.avoid_question_prompts else "none"
        allowed_question_types = ", ".join(question_type.value for question_type in QuestionType)
        return (
            "Generate one Romanian grammar lesson and quiz as structured JSON with the exact top-level keys: "
            "lesson_id, topic, level, cefr_band, difficulty, explanation_text, example_sentences, key_rules, quiz_questions. "
            "The top-level values for topic, level, and cefr_band must exactly match the requested topic id, level, and CEFR band provided below. "
            "Do not substitute another topic id, another CEFR band, or a generic placeholder. "
            "Use those exact snake_case key names and include every required field. "
            "The top-level difficulty field is mandatory and must be an integer from 1 to 10. "
            "Each example_sentences item must have romanian and english. "
            "Write explanation_text, every key_rules item, every example_sentences.english value, every quiz question prompt, every quiz question explanation, and every hint in clear English for the learner. "
            "Only example_sentences.romanian, Romanian answer choices, quoted Romanian source snippets, and correct_answer values for Romanian-output tasks should be in Romanian. "
            "Each quiz_questions item must include question_id, type, prompt, options, correct_answer, explanation, difficulty, tags, hint, rubric, and cefr_band. "
            f"Allowed question type values are exactly: {allowed_question_types}. "
            "Do not invent aliases such as translation, multiple-choice, rewrite_sentence, reading, or writing_prompt. "
            "Each quiz question difficulty field is mandatory and must be an integer from 1 to 10. "
            "Length limits are strict: explanation_text <= 800 characters; each example_sentences.romanian and example_sentences.english <= 180 characters; each quiz question prompt <= 320 characters; each quiz question explanation <= 500 characters. "
            "If strict validation mode is yes, correct every validation issue exactly as listed and keep all affected fields within those limits. "
            "Rubric must always be a JSON object. Use {} for non-guided-writing questions; only guided_writing items should have non-empty rubric criteria. "
            "Every question tags list must include the current topic id or one of the topic grammar-focus tags, and must not use tags from unrelated roadmap topics. "
            f"Topic id: {topic.topic_id}. "
            f"Topic title: {topic.title}. "
            f"Level: {topic.level}. "
            f"CEFR band: {topic.cefr_band.value}. "
            f"Prerequisites already modeled by the app: {prerequisite_text}. "
            f"Learner current level: {request.user_progress.current_level}. "
            f"Learner current CEFR estimate: {request.user_progress.current_cefr_band.value}. "
            f"Recent quiz scores: {recent_scores}. "
            f"Requested session goal: {request.session_goal}. "
            f"Recommended next difficulty from the adaptive engine: {constraints.difficulty}. "
            f"Adaptive action: {assessment.action.value}. "
            f"Vocabulary profile: {constraints.vocabulary_profile}. "
            f"Sentence profile: {constraints.sentence_profile}. "
            f"Scaffolding profile: {constraints.scaffolding}. "
            f"Novelty profile: {constraints.novelty}. "
            f"Include hints: {'yes' if constraints.include_hints else 'no'}. "
            f"Maximum connected context sentences per item: {constraints.max_context_sentences}. "
            f"Focus tags from recent learner errors: {focus_tags}. "
            f"Blocked topics that must not appear: {blocked_topics}. "
            f"Recently answered-correct question prompts to avoid reusing for this learner: {avoid_question_prompts}. "
            f"Produce exactly {request.question_count} quiz questions. "
            "Use common daily vocabulary suitable for English speakers learning Romanian. "
            "Prefer one main concept per question unless the learner is already working at B1 or B2 and integrated practice is appropriate. "
            "If the target CEFR band is B1 or above, every example_sentences item must itself be multi-clause or multi-sentence, not a short single clause. "
            "For B1-B2 examples, use connected context with punctuation or connectors such as dar, deoarece, desi, ca sa, or in timp ce. "
            "If the target CEFR band is B1 or above, include at least one sentence_transformation or dialogue_completion question. "
            "For sentence_transformation, dialogue_completion, guided_writing, and reading_comprehension items, options may be an empty list but the prompt must provide enough context and the correct_answer must still be a concrete reference answer. "
            "Keep B1 vocabulary practical: messages, plans, travel, work, preferences, obligations, and short narrative events. "
            "If the target CEFR band is B2, include at least one reading_comprehension task and one guided_writing task. "
            "Every guided_writing rubric must have at least two named criteria, for example task_completion, accuracy, connector_control, organisation, or register; never use an empty rubric for guided_writing. "
            "B2 prompts should support opinion, comparison, justification, reported speech, connector control, or passive and impersonal structures in coherent paragraph-level contexts. "
            "Do not reuse or paraphrase the recently answered-correct prompts listed above; produce genuinely different questions for this learner. "
            "Before returning JSON, self-check that every B1-B2 example is connected context and every guided_writing rubric has at least two criteria. "
            f"Validation feedback from previous failed attempts: {validation_feedback}. "
            f"Strict validation mode: {'yes' if request.strict_validation else 'no'}."
        )


@dataclass(slots=True)
class PromptBuilder:
    system_builder: SystemPromptBuilder = field(default_factory=SystemPromptBuilder)
    lesson_builder: LessonPromptBuilder = field(default_factory=LessonPromptBuilder)

    def build_lesson_prompt(
        self,
        request: LessonGenerationRequest,
        topic: TopicMetadata,
        assessment: DifficultyAssessment,
        constraints: PromptConstraints,
    ) -> PromptPackage:
        context = PromptContext(
            topic_id=topic.topic_id,
            topic_title=topic.title,
            level=topic.level,
            cefr_band=constraints.cefr_band,
            difficulty=constraints.difficulty,
            session_goal=request.session_goal,
            recent_scores=tuple(request.user_progress.recent_scores),
            focus_tags=tuple(request.focus_tags),
            blocked_topics=constraints.blocked_topics,
        )
        metadata = {
            "topic_id": topic.topic_id,
            "level": topic.level,
            "requested_cefr_band": topic.cefr_band.value,
            "recommended_cefr_band": constraints.cefr_band.value,
            "difficulty": constraints.difficulty,
            "session_goal": request.session_goal,
            "focus_tags": list(request.focus_tags),
            "blocked_topics": list(constraints.blocked_topics),
            "question_count": request.question_count,
            "strict_validation": request.strict_validation,
            "validation_feedback": list(request.validation_feedback),
            "avoid_question_prompts": list(request.avoid_question_prompts),
        }
        return PromptPackage(
            messages=(
                AIMessage(role="system", content=self.system_builder.build(context)),
                AIMessage(
                    role="user",
                    content=self.lesson_builder.build(request, topic, assessment, constraints),
                ),
            ),
            metadata=metadata,
        )
