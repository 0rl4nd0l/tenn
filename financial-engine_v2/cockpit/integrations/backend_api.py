from __future__ import annotations

from typing import Any

import httpx


class BackendApiClient:
    def __init__(self, base_url: str, *, api_key: str = "") -> None:
        self.base_url = self._normalize_base_url(base_url)
        self.api_key = str(api_key or "").strip()

    def _api_key_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _ops_get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, params=params, headers=self._api_key_headers())
            response.raise_for_status()
            return response.json() if response.content else {}

    def _ops_post(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.post(
                url,
                params=params,
                json=json,
                headers=self._api_key_headers(),
            )
            response.raise_for_status()
            return response.json() if response.content else {}

    def health(self, timeout: float = 5.0) -> dict[str, Any]:
        url = f"{self.base_url}/api/health"
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            try:
                response = client.get(url)
                response.raise_for_status()
                payload = response.json() if response.content else {}
                return {"ok": True, "url": self.base_url, "payload": payload}
            except Exception as exc:
                return {"ok": False, "url": self.base_url, "error": str(exc)}

    def capabilities(self, timeout: float = 5.0) -> dict[str, Any]:
        url = f"{self.base_url}/api/system/capabilities"
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            try:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                payload = response.json() if response.content else {}
                return {"ok": True, "url": self.base_url, "payload": payload}
            except httpx.HTTPStatusError as exc:
                detail = None
                try:
                    body = exc.response.json() if exc.response is not None else {}
                    detail = body.get("detail")
                except Exception:
                    detail = None
                code = (
                    exc.response.status_code if exc.response is not None else "unknown"
                )
                return {
                    "ok": False,
                    "url": self.base_url,
                    "status_code": code,
                    "error": str(detail or f"HTTP {code}"),
                }
            except Exception as exc:
                return {"ok": False, "url": self.base_url, "error": str(exc)}

    def apply_proposal(self, proposal_id: str, timeout: float = 30.0) -> dict[str, Any]:
        url = f"{self.base_url}/api/system/proposals/apply"
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            try:
                response = client.post(
                    url, json={"proposal_id": proposal_id}, headers=headers
                )
                response.raise_for_status()
                payload = response.json() if response.content else {}
                return {"ok": True, "url": self.base_url, "payload": payload}
            except httpx.HTTPStatusError as exc:
                detail = None
                try:
                    body = exc.response.json() if exc.response is not None else {}
                    detail = body.get("detail")
                except Exception:
                    detail = None
                code = (
                    exc.response.status_code if exc.response is not None else "unknown"
                )
                return {
                    "ok": False,
                    "url": self.base_url,
                    "status_code": code,
                    "error": str(detail or f"HTTP {code}"),
                }
            except Exception as exc:
                return {"ok": False, "url": self.base_url, "error": str(exc)}

    def queue_action_job(
        self,
        action_id: str,
        args: dict[str, Any],
        *,
        session_id: str | None = None,
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "action_id": str(action_id or "").strip(),
            "args": args,
            "wait": False,
        }
        if session_id is not None:
            payload["session_id"] = str(session_id or "").strip() or None
        return self._ops_post(
            "/api/cockpit/action/execute",
            json=payload,
            timeout=timeout,
        )

    def get_action_job(
        self,
        job_id: str,
        *,
        tail: int = 0,
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        params: dict[str, Any] | None = {"tail": tail} if tail else None
        return self._ops_get(
            f"/api/cockpit/action/jobs/{str(job_id or '').strip()}",
            params=params,
            timeout=timeout,
        )

    def stop_action_job(self, job_id: str, timeout: float = 15.0) -> dict[str, Any]:
        return self._ops_post(
            f"/api/cockpit/action/jobs/{str(job_id or '').strip()}/stop",
            timeout=timeout,
        )

    def list_cockpit_holdings(
        self,
        *,
        ticker: str | None = None,
        include_archived: bool = False,
        timeout: float = 20.0,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "include_archived": "true" if include_archived else "false"
        }
        if ticker is not None:
            params["ticker"] = str(ticker).strip().upper()
        return self._ops_get(
            "/api/cockpit/holdings",
            params=params,
            timeout=timeout,
        )

    def start_action_job(
        self,
        action_id: str,
        args: dict[str, Any] | None = None,
        *,
        session_id: str | None = None,
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        return self.queue_action_job(
            action_id,
            args or {},
            session_id=session_id,
            timeout=timeout,
        )

    def get_price(
        self,
        ticker: str,
        exchange: str = "ASX",
        range_: str = "3mo",
        interval: str = "1d",
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/price"
        params = {
            "ticker": str(ticker or "").strip().upper(),
            "exchange": str(exchange or "").strip().upper(),
            "range": str(range_ or "").strip(),
            "interval": str(interval or "").strip(),
        }
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            try:
                response = client.get(url, params=params)
                response.raise_for_status()
                payload = response.json() if response.content else {}
                return {"ok": True, "url": self.base_url, "payload": payload}
            except httpx.HTTPStatusError as exc:
                detail = None
                try:
                    body = exc.response.json() if exc.response is not None else {}
                    detail = body.get("detail")
                except Exception:
                    detail = None
                code = (
                    exc.response.status_code if exc.response is not None else "unknown"
                )
                message = str(detail or f"HTTP {code}")
                return {
                    "ok": False,
                    "url": self.base_url,
                    "status_code": code,
                    "error": message,
                }
            except Exception as exc:
                return {"ok": False, "url": self.base_url, "error": str(exc)}

    def rag_query(
        self,
        q: str,
        top_k: int = 10,
        ticker: str | None = None,
        provider: str | None = None,
        language: str = "en",
        date_from: str | None = None,
        date_to: str | None = None,
        timeout: float = 15.0,
        source: str = "news",
    ) -> dict[str, Any]:
        url = f"{self.base_url}/rag/query"
        body: dict[str, Any] = {
            "query": q,
            "source": source,
            "top_k": top_k,
        }
        if ticker is not None:
            body["ticker"] = ticker
        if provider is not None:
            body["provider"] = provider
        if language:
            body["language"] = language
        if date_from is not None:
            body["date_from"] = date_from
        if date_to is not None:
            body["date_to"] = date_to
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.post(url, json=body, headers=headers)
            response.raise_for_status()
            return response.json() if response.content else {"results": []}

    def synthesize_research(
        self,
        ticker: str,
        gathered_sources: dict[str, Any],
        *,
        focus: str | None = None,
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        """Call POST /research/synthesize to synthesize gathered sources into a brief.

        Uses a long timeout (120s default) because LLM synthesis can be slow.
        """
        url = f"{self.base_url}/research/synthesize"
        body: dict[str, Any] = {
            "ticker": str(ticker or "").strip().upper(),
            "gathered_sources": gathered_sources,
        }
        if focus:
            body["focus"] = str(focus).strip()
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            try:
                response = client.post(url, json=body, headers=headers)
                response.raise_for_status()
                return response.json() if response.content else {}
            except httpx.HTTPStatusError as exc:
                detail = None
                try:
                    err_body = exc.response.json() if exc.response is not None else {}
                    detail = err_body.get("detail")
                except Exception:
                    pass
                code = (
                    exc.response.status_code if exc.response is not None else "unknown"
                )
                raise RuntimeError(
                    f"Synthesis failed (HTTP {code}): {detail or exc}"
                ) from exc
            except httpx.TimeoutException as exc:
                raise RuntimeError(
                    f"Synthesis timed out after {timeout}s: {exc}"
                ) from exc

    # ------------------------------------------------------------------
    # Context endpoints (Stage A — backend-authority migration)
    # ------------------------------------------------------------------

    def get_ticker_context(
        self,
        ticker: str,
        *,
        docs_limit: int | None = None,
        financials_limit: int | None = None,
        announcements_limit: int | None = None,
        failures_limit: int | None = None,
        low_confidence_threshold: float | None = None,
        low_confidence_limit: int | None = None,
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/context/ticker"
        params: dict[str, Any] = {"ticker": str(ticker or "").strip().upper()}
        if docs_limit is not None:
            params["docs_limit"] = docs_limit
        if financials_limit is not None:
            params["financials_limit"] = financials_limit
        if announcements_limit is not None:
            params["announcements_limit"] = announcements_limit
        if failures_limit is not None:
            params["failures_limit"] = failures_limit
        if low_confidence_threshold is not None:
            params["low_confidence_threshold"] = low_confidence_threshold
        if low_confidence_limit is not None:
            params["low_confidence_limit"] = low_confidence_limit
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json() if response.content else {}

    def get_verification_context(
        self,
        ticker: str | None = None,
        *,
        failures_limit: int | None = None,
        low_confidence_threshold: float | None = None,
        low_confidence_limit: int | None = None,
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/context/verification"
        params: dict[str, Any] = {}
        if ticker is not None:
            params["ticker"] = str(ticker).strip().upper()
        if failures_limit is not None:
            params["failures_limit"] = failures_limit
        if low_confidence_threshold is not None:
            params["low_confidence_threshold"] = low_confidence_threshold
        if low_confidence_limit is not None:
            params["low_confidence_limit"] = low_confidence_limit
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json() if response.content else {}

    def get_company_dump(
        self,
        ticker: str,
        *,
        docs_limit: int | None = None,
        financials_limit: int | None = None,
        announcements_limit: int | None = None,
        failures_limit: int | None = None,
        low_confidence_threshold: float | None = None,
        low_confidence_limit: int | None = None,
        risk_notes_limit: int | None = None,
        company_memory_entries_limit: int | None = None,
        company_memory_change_limit: int | None = None,
        market_memory_limit: int | None = None,
        timeout: float = 20.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/context/company_dump"
        params: dict[str, Any] = {"ticker": str(ticker or "").strip().upper()}
        if docs_limit is not None:
            params["docs_limit"] = docs_limit
        if financials_limit is not None:
            params["financials_limit"] = financials_limit
        if announcements_limit is not None:
            params["announcements_limit"] = announcements_limit
        if failures_limit is not None:
            params["failures_limit"] = failures_limit
        if low_confidence_threshold is not None:
            params["low_confidence_threshold"] = low_confidence_threshold
        if low_confidence_limit is not None:
            params["low_confidence_limit"] = low_confidence_limit
        if risk_notes_limit is not None:
            params["risk_notes_limit"] = risk_notes_limit
        if company_memory_entries_limit is not None:
            params["company_memory_entries_limit"] = company_memory_entries_limit
        if company_memory_change_limit is not None:
            params["company_memory_change_limit"] = company_memory_change_limit
        if market_memory_limit is not None:
            params["market_memory_limit"] = market_memory_limit
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json() if response.content else {}

    def get_memory_dump(
        self,
        ticker: str,
        *,
        company_memory_entries_limit: int | None = None,
        company_memory_change_limit: int | None = None,
        market_memory_limit: int | None = None,
        timeout: float = 20.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/context/memory"
        params: dict[str, Any] = {"ticker": str(ticker or "").strip().upper()}
        if company_memory_entries_limit is not None:
            params["company_memory_entries_limit"] = company_memory_entries_limit
        if company_memory_change_limit is not None:
            params["company_memory_change_limit"] = company_memory_change_limit
        if market_memory_limit is not None:
            params["market_memory_limit"] = market_memory_limit
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(
                url,
                params=params,
                headers=self._api_key_headers(),
            )
            response.raise_for_status()
            return response.json() if response.content else {}

    def add_company_memory_note(
        self,
        ticker: str,
        statement: str,
        *,
        type_: str = "observed_fact",
        confidence: float = 0.75,
        materiality: float = 0.7,
        persistence: str = "medium",
        timeout: float = 20.0,
    ) -> dict[str, Any]:
        return self._ops_post(
            "/api/context/memory/company/add",
            json={
                "ticker": str(ticker or "").strip().upper(),
                "statement": str(statement or "").strip(),
                "type": str(type_ or "").strip().lower(),
                "confidence": float(confidence),
                "materiality": float(materiality),
                "persistence": str(persistence or "").strip().lower(),
            },
            timeout=timeout,
        )

    def expire_company_memory_entry(
        self,
        ticker: str,
        entry_id: int,
        *,
        timeout: float = 20.0,
    ) -> dict[str, Any]:
        return self._ops_post(
            "/api/context/memory/company/expire",
            json={
                "ticker": str(ticker or "").strip().upper(),
                "entry_id": int(entry_id),
            },
            timeout=timeout,
        )

    def add_market_memory_note(
        self,
        ticker: str,
        statement: str,
        *,
        scope: str = "sector",
        type_: str | None = None,
        confidence: float = 0.75,
        materiality: float = 0.7,
        persistence: str = "medium",
        timeout: float = 20.0,
    ) -> dict[str, Any]:
        normalized_scope = str(scope or "sector").strip().lower()
        default_type = "sector_trend" if normalized_scope == "sector" else "macro_theme"
        return self._ops_post(
            "/api/context/memory/market/add",
            json={
                "ticker": str(ticker or "").strip().upper(),
                "statement": str(statement or "").strip(),
                "scope": normalized_scope,
                "type": str(type_ or default_type).strip().lower(),
                "confidence": float(confidence),
                "materiality": float(materiality),
                "persistence": str(persistence or "").strip().lower(),
            },
            timeout=timeout,
        )

    def expire_market_memory_entry(
        self,
        entry_id: int,
        *,
        scope: str,
        timeout: float = 20.0,
    ) -> dict[str, Any]:
        return self._ops_post(
            "/api/context/memory/market/expire",
            json={
                "entry_id": int(entry_id),
                "scope": str(scope or "").strip().lower(),
            },
            timeout=timeout,
        )

    def get_user_thesis_memory(
        self,
        ticker: str,
        *,
        entries_limit: int | None = None,
        proposals_limit: int | None = None,
        timeout: float = 20.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/context/thesis"
        params: dict[str, Any] = {"ticker": str(ticker or "").strip().upper()}
        if entries_limit is not None:
            params["entries_limit"] = entries_limit
        if proposals_limit is not None:
            params["proposals_limit"] = proposals_limit
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(
                url,
                params=params,
                headers=self._api_key_headers(),
            )
            response.raise_for_status()
            return response.json() if response.content else {}

    def create_user_thesis_proposal(
        self,
        *,
        ticker: str,
        proposal_type: str,
        statement: str,
        signal: str | None = None,
        confidence: float = 0.7,
        is_supporting: bool = True,
        note: str | None = None,
        metadata: dict[str, Any] | None = None,
        timeout: float = 20.0,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "ticker": str(ticker or "").strip().upper(),
            "proposal_type": str(proposal_type or "").strip().lower(),
            "statement": str(statement or "").strip(),
            "signal": str(signal).strip().upper() if signal else None,
            "confidence": float(confidence),
            "is_supporting": bool(is_supporting),
            "note": str(note or "").strip() or None,
            "metadata": dict(metadata or {}),
        }
        return self._ops_post(
            "/api/context/thesis/proposals",
            json=body,
            timeout=timeout,
        )

    def confirm_user_thesis_proposal(
        self,
        proposal_id: str,
        *,
        note: str | None = None,
        timeout: float = 20.0,
    ) -> dict[str, Any]:
        return self._ops_post(
            f"/api/context/thesis/proposals/{str(proposal_id or '').strip()}/confirm",
            json={"note": str(note or "").strip() or None},
            timeout=timeout,
        )

    def reject_user_thesis_proposal(
        self,
        proposal_id: str,
        *,
        note: str | None = None,
        timeout: float = 20.0,
    ) -> dict[str, Any]:
        return self._ops_post(
            f"/api/context/thesis/proposals/{str(proposal_id or '').strip()}/reject",
            json={"note": str(note or "").strip() or None},
            timeout=timeout,
        )

    def apply_user_thesis_proposal(
        self,
        proposal_id: str,
        *,
        timeout: float = 20.0,
    ) -> dict[str, Any]:
        return self._ops_post(
            f"/api/context/thesis/proposals/{str(proposal_id or '').strip()}/apply",
            timeout=timeout,
        )

    def process_document(
        self,
        document_id: str,
        *,
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/process/document/{str(document_id or '').strip()}"
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.post(url, headers=headers)
            response.raise_for_status()
            return response.json() if response.content else {}

    def create_extraction_review_session(
        self,
        document_ids: list[str] | None = None,
        run_ids: list[str] | None = None,
        *,
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/extraction-review/session"
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.post(
                url,
                json={
                    "document_ids": [
                        str(document_id).strip()
                        for document_id in (document_ids or [])
                        if str(document_id).strip()
                    ],
                    "run_ids": [
                        str(run_id).strip()
                        for run_id in (run_ids or [])
                        if str(run_id).strip()
                    ],
                },
                headers=headers,
            )
            response.raise_for_status()
            return response.json() if response.content else {}

    def list_extraction_review_runs(
        self,
        *,
        ticker: str | None = None,
        limit: int | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/extraction-review/runs"
        params: dict[str, Any] = {}
        if ticker is not None:
            params["ticker"] = str(ticker).strip().upper()
        if limit is not None:
            params["limit"] = limit
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(
                url,
                params=params,
                headers=self._api_key_headers(),
            )
            response.raise_for_status()
            return response.json() if response.content else {"count": 0, "items": []}

    def get_extraction_review_session(
        self,
        session_id: str,
        *,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/extraction-review/session/{str(session_id or '').strip()}"
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, headers=self._api_key_headers())
            response.raise_for_status()
            return response.json() if response.content else {}

    def submit_extraction_review_decision(
        self,
        session_id: str,
        *,
        item_id: str,
        status: str,
        expected_value: Any | None = None,
        reviewer_note: str | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/extraction-review/session/{str(session_id or '').strip()}/decision"
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        body = {
            "item_id": str(item_id or "").strip(),
            "status": str(status or "").strip().lower(),
            "expected_value": expected_value,
            "reviewer_note": reviewer_note,
        }
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.post(url, json=body, headers=headers)
            response.raise_for_status()
            return response.json() if response.content else {}

    def get_extraction_review_errors(
        self,
        *,
        limit: int | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/extraction-review/errors"
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(
                url,
                params=params,
                headers=self._api_key_headers(),
            )
            response.raise_for_status()
            return response.json() if response.content else {}

    # ------------------------------------------------------------------
    # Ops endpoints
    # ------------------------------------------------------------------

    def list_ops_jobs(
        self,
        status: str | None = None,
        job_type: str | None = None,
        ticker: str | None = None,
        limit: int = 50,
        offset: int = 0,
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status is not None:
            params["status"] = str(status).strip()
        if job_type is not None:
            params["job_type"] = str(job_type).strip()
        if ticker is not None:
            params["ticker"] = str(ticker).strip().upper()
        return self._ops_get("/api/ops/jobs", params=params, timeout=timeout)

    def list_active_ops_jobs(self, timeout: float = 15.0) -> dict[str, Any]:
        return self._ops_get("/api/ops/jobs/active", timeout=timeout)

    def get_ops_job(self, job_id: str, timeout: float = 15.0) -> dict[str, Any]:
        return self._ops_get(
            f"/api/ops/jobs/{str(job_id or '').strip()}",
            timeout=timeout,
        )

    def get_ops_job_events(
        self,
        job_id: str,
        limit: int = 200,
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        return self._ops_get(
            f"/api/ops/jobs/{str(job_id or '').strip()}/events",
            params={"limit": limit},
            timeout=timeout,
        )

    def get_ops_job_artifacts(
        self,
        job_id: str,
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        return self._ops_get(
            f"/api/ops/jobs/{str(job_id or '').strip()}/artifacts",
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Commentary endpoints (Stage A — backend-authority migration)
    # ------------------------------------------------------------------

    def approve_transcript(
        self,
        source_id: str,
        *,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/commentary/transcripts/{source_id}/approve"
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.post(url, headers=headers)
            response.raise_for_status()
            return response.json() if response.content else {}

    def get_pending_transcripts(self, *, timeout: float = 10.0) -> dict[str, Any]:
        url = f"{self.base_url}/api/commentary/transcripts/pending"
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, headers=self._api_key_headers())
            response.raise_for_status()
            return response.json() if response.content else {"pending": [], "count": 0}

    def reject_transcript(
        self,
        source_id: str,
        *,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/commentary/transcripts/{source_id}/reject"
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.post(url, headers=headers)
            response.raise_for_status()
            return response.json() if response.content else {}

    def update_transcript_review(
        self,
        source_id: str,
        *,
        credibility_weight: float | None = None,
        takeaways: list[str] | None = None,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/commentary/transcripts/{source_id}/review"
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        payload: dict[str, Any] = {}
        if credibility_weight is not None:
            payload["credibility_weight"] = credibility_weight
        if takeaways is not None:
            payload["takeaways"] = takeaways
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.patch(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json() if response.content else {}

    def purge_expired_transcripts(
        self,
        *,
        max_age_days: int = 7,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/commentary/transcripts/purge-expired"
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.post(
                url, params={"max_age_days": max_age_days}, headers=headers
            )
            response.raise_for_status()
            return response.json() if response.content else {"purged": [], "count": 0}

    def ingest_url(
        self,
        url: str,
        *,
        credibility_weight: float | None = None,
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        endpoint_url = f"{self.base_url}/api/commentary/ingest-url"
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        payload: dict[str, Any] = {"url": url}
        if credibility_weight is not None:
            payload["credibility_weight"] = credibility_weight
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.post(endpoint_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json() if response.content else {}

    def ingest_youtube_urls(
        self,
        urls: list[str],
        *,
        credibility_weight: float | None = None,
        takeaway_limit: int = 5,
        timeout: float = 180.0,
    ) -> dict[str, Any]:
        endpoint_url = f"{self.base_url}/api/commentary/ingest-urls"
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        payload: dict[str, Any] = {
            "urls": urls,
            "takeaway_limit": takeaway_limit,
        }
        if credibility_weight is not None:
            payload["credibility_weight"] = credibility_weight
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.post(endpoint_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json() if response.content else {
                "ok": True,
                "results": [],
                "errors": [],
            }

    def get_commentary_takeaways(
        self,
        source_id: str,
        *,
        limit: int = 5,
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        endpoint_url = f"{self.base_url}/api/commentary/takeaways"
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.post(
                endpoint_url,
                json={"source_id": source_id, "limit": limit},
                headers=headers,
            )
            response.raise_for_status()
            return response.json() if response.content else {"takeaways": []}

    def add_watched_channel(
        self,
        name_or_id: str,
        *,
        credibility_weight: float = 0.55,
        enabled: bool = True,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/commentary/channels"
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.post(
                url,
                json={
                    "name_or_id": name_or_id,
                    "credibility_weight": credibility_weight,
                    "enabled": enabled,
                },
                headers=headers,
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = None
                try:
                    body = response.json() if response.content else {}
                    if isinstance(body, dict):
                        detail = body.get("detail")
                except Exception:
                    detail = None
                code = response.status_code
                raise RuntimeError(str(detail or f"HTTP {code}")) from exc
            return response.json() if response.content else {}

    def get_youtube_channel_recent_videos(
        self,
        name_or_id: str,
        *,
        limit: int = 8,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/commentary/channels/recent-videos"
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.post(
                url,
                json={"name_or_id": name_or_id, "limit": limit},
                headers=headers,
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = None
                try:
                    body = response.json() if response.content else {}
                    if isinstance(body, dict):
                        detail = body.get("detail")
                except Exception:
                    detail = None
                code = response.status_code
                raise RuntimeError(str(detail or f"HTTP {code}")) from exc
            return response.json() if response.content else {"videos": [], "count": 0}

    def list_watched_channels(self, *, timeout: float = 10.0) -> dict[str, Any]:
        url = f"{self.base_url}/api/commentary/channels"
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.json() if response.content else {"channels": [], "count": 0}

    @staticmethod
    def _normalize_base_url(raw: str) -> str:
        value = (raw or "").strip()
        if not value:
            value = "http://localhost:8000"
        if "://" not in value:
            value = f"http://{value}"
        return value.rstrip("/")
