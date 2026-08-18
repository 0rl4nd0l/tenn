import importlib
import os
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import news_pipeline.cli_common as cli_common  # noqa: E402


NEWS_ENV_KEYS = (
    "TENN_NEWS_ARTIFACT_ROOT",
    "TENN_NEWS_ARTICLES_DB",
    "TENN_NEWS_CONTEXT_DB",
    "TENN_NEWS_RUNS_ROOT",
)


def _reload_with_env(values: dict[str, str]) -> object:
    original = {key: os.environ.get(key) for key in NEWS_ENV_KEYS}
    try:
        for key in NEWS_ENV_KEYS:
            os.environ.pop(key, None)
        for key, value in values.items():
            os.environ[key] = value
        return importlib.reload(cli_common)
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_news_artifact_root_env_controls_all_default_paths(tmp_path: Path) -> None:
    module = _reload_with_env({"TENN_NEWS_ARTIFACT_ROOT": str(tmp_path)})
    try:
        assert module.DEFAULT_NEWS_ARTIFACT_ROOT == tmp_path.resolve()
        assert module.DEFAULT_NEWS_ARTICLES_DB == tmp_path.resolve() / "news_articles.sqlite"
        assert module.DEFAULT_NEWS_CONTEXT_DB == tmp_path.resolve() / "news.sqlite"
        assert module.DEFAULT_NEWS_RUNS_DIR == tmp_path.resolve() / "news_runs"
        assert module.DEFAULT_NEWS_BASELINE_JSON == tmp_path.resolve() / "news_baseline.json"
        assert module.describe_news_artifact_paths()["news_artifact_root_source"] == (
            "TENN_NEWS_ARTIFACT_ROOT"
        )
    finally:
        importlib.reload(cli_common)


def test_individual_news_path_envs_override_artifact_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    articles = tmp_path / "articles.sqlite"
    context = tmp_path / "context.sqlite"
    runs = tmp_path / "runs"
    module = _reload_with_env(
        {
            "TENN_NEWS_ARTIFACT_ROOT": str(root),
            "TENN_NEWS_ARTICLES_DB": str(articles),
            "TENN_NEWS_CONTEXT_DB": str(context),
            "TENN_NEWS_RUNS_ROOT": str(runs),
        }
    )
    try:
        assert module.DEFAULT_NEWS_ARTICLES_DB == articles.resolve()
        assert module.DEFAULT_NEWS_CONTEXT_DB == context.resolve()
        assert module.DEFAULT_NEWS_RUNS_DIR == runs.resolve()
    finally:
        importlib.reload(cli_common)
