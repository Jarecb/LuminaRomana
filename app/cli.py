from __future__ import annotations

from collections.abc import Sequence
import argparse
import shutil
import sys

from app.bootstrap import create_application
from app.ui import run_dev_server


CEFR_TO_LEVEL = {
    "A1": 1,
    "A2": 5,
    "B1": 7,
    "B2": 9,
}

DEFAULT_OFFLINE_QUESTION_TARGET = 100


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lumina-romana")
    subcommands = parser.add_subparsers(dest="command")
    subcommands.add_parser("serve", help="Run the browser-based learner interface.")
    subcommands.add_parser("status", help="Print configuration and runtime status.")
    subcommands.add_parser("reset-progress", help="Reset the default learner's local progress for testing.")
    subcommands.add_parser(
        "clear-offline-questions",
        help="Delete all archived offline fallback or AI-generated questions.",
    )
    set_progress_parser = subcommands.add_parser(
        "set-progress",
        help="Jump the default learner to a testing level or CEFR band.",
    )
    target_group = set_progress_parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--band", choices=tuple(CEFR_TO_LEVEL), help="Jump to the first level of a CEFR band.")
    target_group.add_argument("--level", type=int, help="Jump to an exact roadmap level.")
    set_progress_parser.add_argument(
        "--difficulty",
        type=int,
        help="Override the default testing difficulty for the target position.",
    )
    sample_parser = subcommands.add_parser(
        "sample-content",
        help="Run the Stage 9 content-quality sampling workflow.",
    )
    sample_parser.add_argument(
        "--topics",
        nargs="*",
        help="Optional topic ids to sample. Defaults to the full roadmap.",
    )
    sample_parser.add_argument(
        "--question-count",
        type=int,
        default=5,
        help="Number of questions per sampled lesson.",
    )
    sample_parser.add_argument(
        "--goal",
        default="lesson",
        choices=("lesson", "review", "practice"),
        help="Session goal to use for the sample run.",
    )
    seed_parser = subcommands.add_parser(
        "seed-offline-questions",
        help=f"Top up the offline question bank to {DEFAULT_OFFLINE_QUESTION_TARGET} archived questions per roadmap topic by default.",
    )
    seed_parser.add_argument(
        "--topics",
        nargs="*",
        help="Optional topic ids to seed. Defaults to the full roadmap from A1 through B2.",
    )
    seed_parser.add_argument(
        "--question-count",
        type=int,
        default=DEFAULT_OFFLINE_QUESTION_TARGET,
        help=f"Minimum archived question count per topic. Defaults to {DEFAULT_OFFLINE_QUESTION_TARGET}.",
    )
    seed_parser.add_argument(
        "--goal",
        default="lesson",
        choices=("lesson", "review", "practice"),
        help="Session goal to use when generating the seed content.",
    )
    args = parser.parse_args(list(argv) if argv is not None else sys.argv[1:])

    app = create_application()
    command = args.command or "status"
    if command == "serve":
        run_dev_server(app)
        return 0
    if command == "reset-progress":
        progress = app.learning_service.reset_progress()
        print(f"Reset learner progress for {progress.user_id}.")
        print("Current level: 1")
        print("Current CEFR band: A1")
        print("Current difficulty: 1")
        return 0
    if command == "clear-offline-questions":
        deleted = app.persistence.offline_questions.delete_all()
        print("Cleared offline question bank.")
        print(f"Questions deleted: {deleted}")
        return 0
    if command == "set-progress":
        target_level = args.level if args.level is not None else CEFR_TO_LEVEL[args.band]
        progress = app.learning_service.set_testing_position(
            level=target_level,
            difficulty=args.difficulty,
        )
        next_topic = app.content_library.next_topic_for_user(progress)
        next_topic_label = next_topic.title if next_topic is not None else "Roadmap complete"
        print(f"Set learner progress for {progress.user_id}.")
        print(f"Current level: {progress.current_level}")
        print(f"Current CEFR band: {progress.current_cefr_band.value}")
        print(f"Current difficulty: {progress.current_difficulty}")
        print(f"Next topic: {next_topic_label}")
        return 0
    if command == "sample-content":
        before = app.ai_service.metrics_snapshot()
        report = app.quality_service.sample_lessons(
            topic_ids=args.topics,
            question_count=args.question_count,
            session_goal=args.goal,
        )
        after = app.ai_service.metrics_snapshot()
        print("Lumina Romana content-quality sample")
        print(f"Samples run: {report.total_samples}")
        print(f"AI-backed samples: {report.ai_samples}")
        print(f"Fallback samples: {report.fallback_samples}")
        print(
            "Metrics delta: "
            f"validation_failures={after.validation_failures - before.validation_failures}, "
            f"retries={after.retries_attempted - before.retries_attempted}, "
            f"fallbacks={after.fallback_generations - before.fallback_generations}"
        )
        for sample in report.samples:
            print(
                f"- {sample.topic_id}: level {sample.level} / {sample.cefr_band} / "
                f"source={sample.source} / question_types={', '.join(sample.question_types)}"
            )
            if sample.warnings:
                print(f"  warnings: {' | '.join(sample.warnings)}")
        return 0
    if command == "seed-offline-questions":
        print(
            "AI provider: "
            f"{app.ai_service.provider.provider_name} "
            f"({app.ai_service.provider.model}, configured={app.ai_service.is_configured})"
        )
        if not app.ai_service.is_configured:
            print("Seeding will use fallback content only because no AI provider is configured for this process.")
        report = app.quality_service.seed_offline_question_bank(
            topic_ids=args.topics,
            question_count=args.question_count,
            session_goal=args.goal,
        )
        print("Lumina Romana offline question bank seed")
        print(f"Topics processed: {report.total_topics}")
        print(f"Questions before: {report.total_questions_before}")
        print(f"Questions after: {report.total_questions_after}")
        print(f"Questions added: {report.total_questions_added}")
        for topic in report.topics:
            print(
                f"- {topic.topic_id}: level {topic.level} / {topic.cefr_band} / "
                f"source={topic.source} / before={topic.stored_question_count_before} / "
                f"after={topic.stored_question_count_after} / added={topic.added_question_count}"
            )
            if topic.warnings:
                print(f"  warnings: {' | '.join(topic.warnings)}")
        return 0

    app.logger.info("Loading %s diagnostics in %s mode", app.settings.app_name, app.settings.environment)
    print(f"{app.settings.app_name} developer status")
    print(f"Environment: {app.settings.environment}")
    print(f"Data directory: {app.settings.data_dir}")
    print(f"Database path: {app.settings.database_path}")
    print(f"Seed topics loaded: {len(app.content_library.all_topics())}")
    print(f"Offline question bank size: {app.persistence.offline_questions.count_all()}")
    print(
        "AI provider: "
        f"{app.ai_service.provider.provider_name} "
        f"({app.ai_service.provider.model}, configured={app.ai_service.is_configured})"
    )
    metrics = app.ai_service.metrics_snapshot()
    print(
        "AI metrics: "
        f"requests={metrics.total_requests}, "
        f"validation_failures={metrics.validation_failures}, "
        f"retries={metrics.retries_attempted}, "
        f"fallbacks={metrics.fallback_generations}"
    )
    print(f"Web UI: http://{app.settings.web.host}:{app.settings.web.port}")
    print("Run `python main.py serve` to start the browser-based learner interface from this checkout.")
    if shutil.which("lumina-romana"):
        print("Installed console script available: `lumina-romana serve`.")
    else:
        print("Install with `pip install -e .` if you want the `lumina-romana` command in your environment.")
    return 0
