#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GROUND_TRUTH = REPO_ROOT / "data" / "ground_truth"
DEFAULT_DOCLING_VENV = REPO_ROOT / ".venv_docling"
DEFAULT_REPORT_DIR = REPO_ROOT / "reports" / "pdf_extraction_benchmark" / "orchestrator"
DEFAULT_MODE = "BATCH_RUN"
DEFAULT_METHODS = "financial_metrics_pdftotext,financial_metrics_docling"
DEFAULT_MIN_DOCUMENTS = 10
DEFAULT_MAX_DOCUMENTS = 12
PDF_EXTENSIONS = (".pdf",)
DOC_TYPE_MAP = {
    "financial_performance": "structured_financial_reports",
    "investor_communications": "semi_structured_presentations",
    "other": "complex_ocr_heavy",
}
METHOD_COST = {
    "financial_metrics_pdftotext": 1.0,
    "financial_metrics_docling": 4.0,
}
DEFAULT_LEARNING_LOOP_ENABLED = False
DEFAULT_FAST_PATH_ENABLED = True
DEFAULT_SLOW_PATH_ENABLED = True
DEFAULT_REVIEW_INTERVAL = 5
DEFAULT_MIN_SAMPLE_COUNT = 5
PREFERENCES_PATH = REPO_ROOT / "services" / "extraction" / "routing_preferences.json"
SKILL_PATH = REPO_ROOT / "services" / "extraction" / "extraction_skill.md"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.evaluation.confidence import CONFIDENCE_THRESHOLD
from services.extraction.routing_preferences import (
    load_preferences,
    save_preferences,
    snapshot_preferences,
)
from services.extraction.preference_updater import update_preferences
from services.extraction.skill_reviewer import should_review, snapshot_skill


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _mode_name(value: Any) -> str:
    key = str(value or DEFAULT_MODE).strip().upper()
    aliases = {
        "BATCH": "BATCH_RUN",
        "BATCH_RUN": "BATCH_RUN",
        "SINGLE": "SINGLE_RUN",
        "SINGLE_RUN": "SINGLE_RUN",
        "ROUTED": "ROUTED_EXTRACTION",
        "ROUTED_EXTRACTION": "ROUTED_EXTRACTION",
        "EVAL": "EVALUATION_ONLY",
        "EVALUATION_ONLY": "EVALUATION_ONLY",
    }
    if key not in aliases:
        raise ValueError(f"unsupported_mode:{value}")
    return aliases[key]


def _python_exec() -> str:
    candidate = REPO_ROOT / "financial-engine_v2" / ".venv" / "bin" / "python"
    if candidate.exists():
        return str(candidate)
    return sys.executable


def _path_key(path: Path) -> str:
    return str(path.expanduser().resolve())


def _dataset_type_from_pdf(pdf_path: Path) -> str:
    label = pdf_path.parent.name.strip().lower()
    return DOC_TYPE_MAP.get(label, label or "unknown")


def _complexity_bucket(score: Any) -> str:
    value = _safe_float(score)
    if value < 0.33:
        return "low"
    if value < 0.66:
        return "medium"
    return "high"


def _distribution(values: list[float]) -> dict[str, float]:
    if not values:
        return {"count": 0, "min": 0.0, "max": 0.0, "mean": 0.0, "p50": 0.0}
    ordered = sorted(float(v) for v in values)
    count = len(ordered)
    midpoint = count // 2
    if count % 2 == 1:
        p50 = ordered[midpoint]
    else:
        p50 = (ordered[midpoint - 1] + ordered[midpoint]) / 2.0
    return {
        "count": count,
        "min": round(ordered[0], 6),
        "max": round(ordered[-1], 6),
        "mean": round(sum(ordered) / float(count), 6),
        "p50": round(p50, 6),
    }


@dataclass(frozen=True)
class DatasetSelection:
    pdfs: list[Path]
    dataset_counts: dict[str, int]
    source_dirs: list[str]


class PipelineOrchestrator:
    def __init__(self, repo_root: str | Path | None = None) -> None:
        self.repo_root = Path(repo_root).expanduser().resolve() if repo_root else REPO_ROOT
        self.report_root = self.repo_root / "reports" / "pdf_extraction_benchmark" / "orchestrator"
        self.report_root.mkdir(parents=True, exist_ok=True)
        self.logs: list[dict[str, str]] = []

    def _log(self, stage: str, decision: str, reason: str) -> None:
        self.logs.append({"stage": stage, "decision": decision, "reason": reason})

    def _run_command(self, command: list[str], *, stage: str) -> subprocess.CompletedProcess[str]:
        self._log(stage, "execute", "subprocess_call")
        return subprocess.run(
            command,
            cwd=str(self.repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

    def _discover_pdfs(self, pdf_dirs: list[Path]) -> dict[str, list[Path]]:
        grouped: dict[str, list[Path]] = {}
        seen: set[str] = set()
        for pdf_dir in pdf_dirs:
            if not pdf_dir.exists() or not pdf_dir.is_dir():
                continue
            for path in sorted(pdf_dir.rglob("*")):
                if not path.is_file():
                    continue
                if path.suffix.lower() not in PDF_EXTENSIONS:
                    continue
                key = _path_key(path)
                if key in seen:
                    continue
                seen.add(key)
                dataset_type = _dataset_type_from_pdf(path)
                grouped.setdefault(dataset_type, []).append(path)
        return grouped

    def _expand_discovery(self, grouped: dict[str, list[Path]], *, target_count: int) -> dict[str, list[Path]]:
        current = sum(len(items) for items in grouped.values())
        if current >= target_count:
            return grouped
        root = self.repo_root / "financial-engine_v2" / "data" / "asx" / "docs"
        if not root.exists():
            return grouped
        seen = {_path_key(path) for paths in grouped.values() for path in paths}
        for path in sorted(root.rglob("*.pdf")):
            key = _path_key(path)
            if key in seen:
                continue
            seen.add(key)
            dataset_type = _dataset_type_from_pdf(path)
            grouped.setdefault(dataset_type, []).append(path)
            current += 1
            if current >= target_count:
                break
        return grouped

    def _round_robin_sample(self, grouped: dict[str, list[Path]], *, max_documents: int) -> list[Path]:
        keys = sorted(grouped.keys())
        for key in keys:
            grouped[key] = list(grouped[key])
        selected: list[Path] = []
        while len(selected) < max_documents:
            progressed = False
            for key in keys:
                bucket = grouped.get(key, [])
                if not bucket:
                    continue
                selected.append(bucket.pop(0))
                progressed = True
                if len(selected) >= max_documents:
                    break
            if not progressed:
                break
        return selected

    def _prepare_datasets(self, config: Mapping[str, Any], mode: str) -> DatasetSelection:
        raw_dirs = list(config.get("pdf_dirs") or [])
        if not raw_dirs:
            raise ValueError("missing_pdf_dirs")
        pdf_dirs = [Path(str(item)).expanduser().resolve() for item in raw_dirs]
        min_documents = _safe_int(config.get("min_documents") or DEFAULT_MIN_DOCUMENTS)
        max_documents = _safe_int(config.get("max_documents") or DEFAULT_MAX_DOCUMENTS)
        if mode == "SINGLE_RUN":
            min_documents = 1
            max_documents = 1
        if max_documents < min_documents:
            max_documents = min_documents
        grouped = self._discover_pdfs(pdf_dirs)
        grouped = self._expand_discovery(grouped, target_count=min_documents)
        selected = self._round_robin_sample(grouped, max_documents=max_documents)
        if len(selected) < min_documents:
            raise RuntimeError("ERROR_INSUFFICIENT_DOCUMENTS_TOTAL")
        dataset_counts: dict[str, int] = {}
        for path in selected:
            dataset = _dataset_type_from_pdf(path)
            dataset_counts[dataset] = dataset_counts.get(dataset, 0) + 1
        return DatasetSelection(
            pdfs=selected,
            dataset_counts=dataset_counts,
            source_dirs=[str(path) for path in pdf_dirs],
        )

    def extraction_agent(
        self,
        *,
        pdfs: list[Path],
        methods: str,
        ground_truth: Path,
        docling_venv: Path,
        subprocess_timeout_sec: float,
        run_root: Path,
        out_json: Path,
        create_docling_venv: bool,
        docling_cpu: bool,
    ) -> dict[str, Any]:
        run_root.mkdir(parents=True, exist_ok=True)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        command = [
            _python_exec(),
            str(self.repo_root / "scripts" / "benchmark_pdf_extraction.py"),
            "--methods",
            methods,
            "--ground-truth",
            str(ground_truth),
            "--docling-venv",
            str(docling_venv),
            "--subprocess-timeout-sec",
            str(float(subprocess_timeout_sec)),
            "--run-root",
            str(run_root),
            "--out-json",
            str(out_json),
        ]
        for pdf in pdfs:
            command.extend(["--pdf", str(pdf)])
        if create_docling_venv:
            command.append("--create-docling-venv")
        if docling_cpu:
            command.append("--docling-cpu")
        completed = self._run_command(command, stage="extraction_agent")
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "extraction_agent_failed")
        return json.loads(out_json.read_text(encoding="utf-8"))

    def benchmark_agent(
        self,
        *,
        pdfs: list[Path],
        methods: str,
        ground_truth: Path,
        docling_venv: Path,
        subprocess_timeout_sec: float,
        run_root: Path,
        out_json: Path,
        create_docling_venv: bool,
        docling_cpu: bool,
    ) -> dict[str, Any]:
        self._log("benchmark_agent", "delegate", "benchmark_pdf_extraction")
        return self.extraction_agent(
            pdfs=pdfs,
            methods=methods,
            ground_truth=ground_truth,
            docling_venv=docling_venv,
            subprocess_timeout_sec=subprocess_timeout_sec,
            run_root=run_root,
            out_json=out_json,
            create_docling_venv=create_docling_venv,
            docling_cpu=docling_cpu,
        )

    def routing_agent(
        self,
        *,
        pdfs: list[Path],
        ground_truth: Path,
        docling_venv: Path,
        subprocess_timeout_sec: float,
        run_root: Path,
        out_json: Path,
        create_docling_venv: bool,
        docling_cpu: bool,
    ) -> dict[str, Any]:
        run_root.mkdir(parents=True, exist_ok=True)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        command = [
            _python_exec(),
            str(self.repo_root / "scripts" / "run_routed_extraction.py"),
            "--ground-truth",
            str(ground_truth),
            "--docling-venv",
            str(docling_venv),
            "--subprocess-timeout-sec",
            str(float(subprocess_timeout_sec)),
            "--run-root",
            str(run_root),
            "--out-json",
            str(out_json),
        ]
        for pdf in pdfs:
            command.extend(["--pdf", str(pdf)])
        if create_docling_venv:
            command.append("--create-docling-venv")
        if docling_cpu:
            command.append("--docling-cpu")
        completed = self._run_command(command, stage="routing_agent")
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "routing_agent_failed")
        return json.loads(out_json.read_text(encoding="utf-8"))

    def anomaly_agent(self, *, routed_payload: Mapping[str, Any]) -> dict[str, Any]:
        documents = list(routed_payload.get("documents") or [])
        total = len(documents)
        has_anomaly = 0
        severity_counts = {"high": 0, "medium": 0, "low": 0}
        for document in documents:
            if not isinstance(document, Mapping):
                continue
            anomaly = document.get("anomaly")
            if not isinstance(anomaly, Mapping):
                continue
            if bool(anomaly.get("has_anomaly")):
                has_anomaly += 1
                severity = str(anomaly.get("severity") or "low").lower()
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
        return {
            "anomaly_rate": round(float(has_anomaly) / float(max(1, total)), 6),
            "severity_counts": severity_counts,
        }

    def evaluation_agent(
        self,
        *,
        full_payload: Mapping[str, Any],
        routed_payload: Mapping[str, Any],
        datasets: DatasetSelection,
        methods: list[str],
    ) -> dict[str, Any]:
        full_documents = list(full_payload.get("documents") or [])
        routed_documents = list(routed_payload.get("documents") or [])
        routed_by_pdf = {
            str(document.get("pdf") or ""): document
            for document in routed_documents
            if isinstance(document, Mapping)
        }
        full_doc_accuracies: list[float] = []
        for full_document in full_documents:
            if not isinstance(full_document, Mapping):
                continue
            method_payloads = dict(full_document.get("methods") or {})
            accuracies: list[float] = []
            for payload in method_payloads.values():
                if not isinstance(payload, Mapping):
                    continue
                score = payload.get("score")
                if not isinstance(score, Mapping):
                    continue
                if str(score.get("status") or "") != "SUCCESS":
                    continue
                aggregate = score.get("aggregate")
                if not isinstance(aggregate, Mapping):
                    continue
                accuracies.append(_safe_float(aggregate.get("accuracy")))
            if accuracies:
                full_doc_accuracies.append(max(accuracies))

        routed_accuracies: list[float] = []
        fallback_count = 0
        fallback_due_to_anomaly = 0
        anomaly_count = 0
        confidences: list[float] = []
        doc_type_distribution: dict[str, int] = {}
        complexity_distribution: dict[str, int] = {"low": 0, "medium": 0, "high": 0}
        fallback_by_doc_type: dict[str, dict[str, int]] = {}
        by_doc_type: dict[str, dict[str, float]] = {}
        by_complexity: dict[str, dict[str, float]] = {}
        by_method: dict[str, dict[str, float]] = {}

        for pdf in datasets.pdfs:
            key = str(pdf)
            routed_document = routed_by_pdf.get(key)
            if not isinstance(routed_document, Mapping):
                continue
            classifier = routed_document.get("classifier")
            if not isinstance(classifier, Mapping):
                classifier = {}
            doc_type = _dataset_type_from_pdf(pdf)
            complexity_score = _safe_float(classifier.get("complexity_score"))
            complexity_bucket = _complexity_bucket(complexity_score)
            selected_method = str(routed_document.get("selected_method") or "unknown")
            fallback_triggered = bool(routed_document.get("fallback_triggered"))
            fallback_reason = str(routed_document.get("fallback_reason") or "")
            confidence = _safe_float(routed_document.get("confidence"))
            anomaly = routed_document.get("anomaly")
            has_anomaly = bool(isinstance(anomaly, Mapping) and anomaly.get("has_anomaly"))
            selected_accuracy = routed_document.get("selected_accuracy")

            doc_type_distribution[doc_type] = doc_type_distribution.get(doc_type, 0) + 1
            complexity_distribution[complexity_bucket] = complexity_distribution.get(complexity_bucket, 0) + 1
            if fallback_triggered:
                fallback_count += 1
            if "financial_anomaly" in fallback_reason:
                fallback_due_to_anomaly += 1
            if has_anomaly:
                anomaly_count += 1
            confidences.append(confidence)

            fallback_bucket = fallback_by_doc_type.setdefault(doc_type, {"documents": 0, "fallbacks": 0})
            fallback_bucket["documents"] += 1
            if fallback_triggered:
                fallback_bucket["fallbacks"] += 1

            doc_type_bucket = by_doc_type.setdefault(doc_type, {"documents": 0.0, "fallbacks": 0.0, "anomalies": 0.0, "accuracy_total": 0.0, "accuracy_count": 0.0})
            doc_type_bucket["documents"] += 1.0
            if fallback_triggered:
                doc_type_bucket["fallbacks"] += 1.0
            if has_anomaly:
                doc_type_bucket["anomalies"] += 1.0
            if isinstance(selected_accuracy, (int, float)):
                doc_type_bucket["accuracy_total"] += float(selected_accuracy)
                doc_type_bucket["accuracy_count"] += 1.0
                routed_accuracies.append(float(selected_accuracy))

            complexity_bucket_entry = by_complexity.setdefault(
                complexity_bucket,
                {"documents": 0.0, "fallbacks": 0.0, "anomalies": 0.0, "accuracy_total": 0.0, "accuracy_count": 0.0},
            )
            complexity_bucket_entry["documents"] += 1.0
            if fallback_triggered:
                complexity_bucket_entry["fallbacks"] += 1.0
            if has_anomaly:
                complexity_bucket_entry["anomalies"] += 1.0
            if isinstance(selected_accuracy, (int, float)):
                complexity_bucket_entry["accuracy_total"] += float(selected_accuracy)
                complexity_bucket_entry["accuracy_count"] += 1.0

            method_bucket = by_method.setdefault(
                selected_method,
                {"documents": 0.0, "fallbacks": 0.0, "anomalies": 0.0, "confidence_total": 0.0, "accuracy_total": 0.0, "accuracy_count": 0.0},
            )
            method_bucket["documents"] += 1.0
            if fallback_triggered:
                method_bucket["fallbacks"] += 1.0
            if has_anomaly:
                method_bucket["anomalies"] += 1.0
            method_bucket["confidence_total"] += confidence
            if isinstance(selected_accuracy, (int, float)):
                method_bucket["accuracy_total"] += float(selected_accuracy)
                method_bucket["accuracy_count"] += 1.0

        full_accuracy = round(sum(full_doc_accuracies) / float(len(full_doc_accuracies)), 6) if full_doc_accuracies else 0.0
        routed_accuracy = round(sum(routed_accuracies) / float(len(routed_accuracies)), 6) if routed_accuracies else 0.0
        documents_total = len(routed_documents)
        fallback_rate = round(float(fallback_count) / float(max(1, documents_total)), 6)
        anomaly_rate = round(float(anomaly_count) / float(max(1, documents_total)), 6)
        fallback_due_to_anomaly_rate = round(float(fallback_due_to_anomaly) / float(max(1, documents_total)), 6)
        confidence_distribution = _distribution(confidences)

        full_cost = 0.0
        for method in methods:
            full_cost += METHOD_COST.get(method, 1.0) * float(documents_total)
        routed_docling_runs = _safe_int((routed_payload.get("summary") or {}).get("docling_runs"))
        routed_cost = METHOD_COST.get("financial_metrics_pdftotext", 1.0) * float(documents_total)
        routed_cost += METHOD_COST.get("financial_metrics_docling", 4.0) * float(routed_docling_runs)
        compute_cost_estimate = round(routed_cost / float(full_cost), 6) if full_cost > 0.0 else 0.0

        for key, bucket in fallback_by_doc_type.items():
            documents = _safe_int(bucket.get("documents"))
            fallbacks = _safe_int(bucket.get("fallbacks"))
            bucket["fallback_rate"] = round(float(fallbacks) / float(max(1, documents)), 6)

        def _finalize(bucket: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
            result: dict[str, dict[str, float]] = {}
            for key, payload in bucket.items():
                documents = _safe_float(payload.get("documents"))
                accuracy_count = _safe_float(payload.get("accuracy_count"))
                output = {
                    "documents": int(documents),
                    "fallback_rate": round(_safe_float(payload.get("fallbacks")) / float(max(1.0, documents)), 6),
                    "anomaly_rate": round(_safe_float(payload.get("anomalies")) / float(max(1.0, documents)), 6),
                }
                if "confidence_total" in payload:
                    output["confidence_mean"] = round(_safe_float(payload.get("confidence_total")) / float(max(1.0, documents)), 6)
                output["accuracy"] = round(_safe_float(payload.get("accuracy_total")) / float(max(1.0, accuracy_count)), 6) if accuracy_count > 0 else 0.0
                result[key] = output
            return result

        return {
            "documents_total": documents_total,
            "datasets": [{"name": name, "documents": count} for name, count in sorted(datasets.dataset_counts.items())],
            "document_type_distribution": doc_type_distribution,
            "complexity_distribution": complexity_distribution,
            "fallback_by_doc_type": fallback_by_doc_type,
            "full_accuracy": full_accuracy,
            "routed_accuracy": routed_accuracy,
            "accuracy": routed_accuracy,
            "fallback_rate": fallback_rate,
            "anomaly_rate": anomaly_rate,
            "fallback_due_to_anomaly_rate": fallback_due_to_anomaly_rate,
            "confidence_distribution": confidence_distribution,
            "compute_cost_estimate": compute_cost_estimate,
            "stratified": {
                "document_type": _finalize(by_doc_type),
                "complexity_bucket": _finalize(by_complexity),
                "extraction_method": _finalize(by_method),
            },
        }

    def _enforce_batch_requirements(self, report: Mapping[str, Any]) -> None:
        documents_total = _safe_int(report.get("documents_total"))
        if documents_total < DEFAULT_MIN_DOCUMENTS:
            raise RuntimeError("ERROR_INSUFFICIENT_DOCUMENTS_TOTAL")
        doc_types = dict(report.get("document_type_distribution") or {})
        unique_document_types = len([key for key, value in doc_types.items() if _safe_int(value) > 0])
        if unique_document_types < 3:
            raise RuntimeError("ERROR_INSUFFICIENT_DATASET_DIVERSITY")
        if "routing" not in report:
            raise RuntimeError("ERROR_ROUTING_NOT_EXECUTED")
        if "fallback_rate" not in report:
            raise RuntimeError("ERROR_MISSING_FALLBACK_METRICS")

    def _extract_method_accuracies(
        self, full_payload: Mapping[str, Any], datasets: DatasetSelection
    ) -> dict[str, dict[str, float]]:
        """Extract per-doc-type, per-method accuracy from full benchmark results."""
        accum: dict[str, dict[str, list[float]]] = {}
        for doc in full_payload.get("documents") or []:
            if not isinstance(doc, Mapping):
                continue
            pdf_path = doc.get("pdf")
            if not pdf_path:
                continue
            doc_type = _dataset_type_from_pdf(Path(str(pdf_path)))
            method_payloads = dict(doc.get("methods") or {})
            for method_name, payload in method_payloads.items():
                if not isinstance(payload, Mapping):
                    continue
                score = payload.get("score")
                if not isinstance(score, Mapping):
                    continue
                if str(score.get("status") or "") != "SUCCESS":
                    continue
                aggregate = score.get("aggregate")
                if not isinstance(aggregate, Mapping):
                    continue
                accuracy = _safe_float(aggregate.get("accuracy"))
                bucket = accum.setdefault(doc_type, {})
                bucket.setdefault(method_name, []).append(accuracy)
        result: dict[str, dict[str, float]] = {}
        for doc_type, methods in accum.items():
            result[doc_type] = {
                method: round(sum(values) / len(values), 6)
                for method, values in methods.items()
                if values
            }
        return result

    def run(self, config: dict) -> dict:
        mode = _mode_name(config.get("mode"))
        ground_truth = Path(str(config.get("ground_truth") or DEFAULT_GROUND_TRUTH)).expanduser().resolve()
        docling_venv = Path(str(config.get("docling_venv") or DEFAULT_DOCLING_VENV)).expanduser().resolve()
        subprocess_timeout_sec = _safe_float(config.get("subprocess_timeout_sec") or 30.0)
        methods = str(config.get("methods") or DEFAULT_METHODS).strip() or DEFAULT_METHODS
        create_docling_venv = bool(config.get("create_docling_venv"))
        docling_cpu = bool(config.get("docling_cpu"))
        enable_fallback = bool(config.get("enable_fallback", True))
        enable_anomaly_detection = bool(config.get("enable_anomaly_detection", True))

        self._log("orchestrator", "mode_selected", mode)
        selection = self._prepare_datasets(config, mode)
        selected_pdfs = selection.pdfs

        base_dir = self.report_root / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        base_dir.mkdir(parents=True, exist_ok=True)
        full_json = base_dir / "full_benchmark.json"
        routed_json = base_dir / "routed_extraction.json"
        full_runs = base_dir / "full_runs"
        routed_runs = base_dir / "routed_runs"

        if mode == "EVALUATION_ONLY":
            full_path = Path(str(config.get("full_benchmark_json") or "")).expanduser().resolve()
            routed_path = Path(str(config.get("routed_json") or "")).expanduser().resolve()
            if not full_path.exists() or not routed_path.exists():
                raise RuntimeError("missing_evaluation_inputs")
            full_payload = json.loads(full_path.read_text(encoding="utf-8"))
            routed_payload = json.loads(routed_path.read_text(encoding="utf-8"))
        else:
            full_payload = self.benchmark_agent(
                pdfs=selected_pdfs,
                methods=methods,
                ground_truth=ground_truth,
                docling_venv=docling_venv,
                subprocess_timeout_sec=subprocess_timeout_sec,
                run_root=full_runs,
                out_json=full_json,
                create_docling_venv=create_docling_venv,
                docling_cpu=docling_cpu,
            )
            if mode == "SINGLE_RUN":
                selected_pdfs = selected_pdfs[:1]
            routed_payload = self.routing_agent(
                pdfs=selected_pdfs,
                ground_truth=ground_truth,
                docling_venv=docling_venv,
                subprocess_timeout_sec=subprocess_timeout_sec,
                run_root=routed_runs,
                out_json=routed_json,
                create_docling_venv=create_docling_venv,
                docling_cpu=docling_cpu,
            )

        method_list = [item.strip() for item in methods.split(",") if item.strip()]
        evaluation = self.evaluation_agent(
            full_payload=full_payload,
            routed_payload=routed_payload,
            datasets=selection,
            methods=method_list,
        )
        anomaly_summary = self.anomaly_agent(routed_payload=routed_payload) if enable_anomaly_detection else {}

        report = {
            "status": "SUCCESS",
            "generated_at_utc": _utc_now(),
            "mode": mode,
            "config": {
                "mode": mode,
                "pdf_dirs": selection.source_dirs,
                "ground_truth": str(ground_truth),
                "docling_venv": str(docling_venv),
                "enable_fallback": enable_fallback,
                "enable_anomaly_detection": enable_anomaly_detection,
                "confidence_threshold": CONFIDENCE_THRESHOLD,
            },
            "datasets": evaluation.get("datasets", []),
            "documents_total": evaluation.get("documents_total", 0),
            "document_type_distribution": evaluation.get("document_type_distribution", {}),
            "complexity_distribution": evaluation.get("complexity_distribution", {}),
            "full_accuracy": evaluation.get("full_accuracy", 0.0),
            "routed_accuracy": evaluation.get("routed_accuracy", 0.0),
            "accuracy": evaluation.get("accuracy", 0.0),
            "fallback_rate": evaluation.get("fallback_rate", 0.0),
            "anomaly_rate": evaluation.get("anomaly_rate", 0.0),
            "fallback_due_to_anomaly_rate": evaluation.get("fallback_due_to_anomaly_rate", 0.0),
            "confidence_distribution": evaluation.get("confidence_distribution", {}),
            "compute_cost_estimate": evaluation.get("compute_cost_estimate", 0.0),
            "fallback_by_doc_type": evaluation.get("fallback_by_doc_type", {}),
            "stratified": evaluation.get("stratified", {}),
            "routing": {
                "summary": routed_payload.get("summary", {}),
                "documents": routed_payload.get("documents", []),
            },
            "full_benchmark": {
                "summary": full_payload.get("summary", {}),
                "method_comparison": full_payload.get("method_comparison", {}),
            },
            "anomaly_summary": anomaly_summary,
            "logs": self.logs,
            "artifacts": {
                "full_benchmark_json": str(full_json),
                "routed_extraction_json": str(routed_json),
                "full_runs_dir": str(full_runs),
                "routed_runs_dir": str(routed_runs),
            },
        }

        # --- Learning Loop ---
        learning_config = config.get("learning_loop") or {}
        if learning_config.get("enabled", DEFAULT_LEARNING_LOOP_ENABLED):
            fast_path_config = learning_config.get("fast_path") or {}
            if fast_path_config.get("enabled", DEFAULT_FAST_PATH_ENABLED):
                self._log("learning_loop", "fast_path", "updating_preferences")
                prefs_path = Path(str(
                    fast_path_config.get("preferences_file") or PREFERENCES_PATH
                ))
                current_prefs = load_preferences(prefs_path)
                snapshot_preferences(prefs_path)
                method_accuracies = self._extract_method_accuracies(
                    full_payload, selection
                )
                new_prefs = update_preferences(
                    assessment_report=evaluation,
                    method_accuracies=method_accuracies,
                    current_prefs=current_prefs,
                    min_sample_count=int(
                        fast_path_config.get("min_sample_count", DEFAULT_MIN_SAMPLE_COUNT)
                    ),
                )
                save_preferences(prefs_path, new_prefs)
                report["learning_loop"] = {"fast_path": "updated"}

            slow_path_config = learning_config.get("slow_path") or {}
            if slow_path_config.get("enabled", DEFAULT_SLOW_PATH_ENABLED):
                review_interval = int(
                    slow_path_config.get("review_interval", DEFAULT_REVIEW_INTERVAL)
                )
                runs_since = int(learning_config.get("_runs_since_review", 0))
                if should_review(runs_since, review_interval):
                    self._log("learning_loop", "slow_path", "review_triggered")
                    skill_path = Path(str(
                        slow_path_config.get("skill_file") or SKILL_PATH
                    ))
                    snapshot_skill(skill_path)
                    report.setdefault("learning_loop", {})["slow_path"] = "review_triggered"
                else:
                    report.setdefault("learning_loop", {})["slow_path"] = "skipped"

        if mode == "BATCH_RUN":
            self._enforce_batch_requirements(report)
        return report
