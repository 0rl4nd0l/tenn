import { useEffect, useMemo, useState } from "react";
import type { EventRecord, ProviderCapabilitySnapshot, TaskDetailPayload } from "../../shared/types";

type DetailTab = "progress" | "review" | "route";

interface TaskDetailPaneProps {
  detail: TaskDetailPayload | null;
  loadingTaskId: string | null;
  actionPending: boolean;
  capabilities: ProviderCapabilitySnapshot[];
  onRetry(taskId: string): Promise<void>;
  onApprove(taskId: string): Promise<void>;
  onReject(taskId: string): Promise<void>;
  onReopen(taskId: string): Promise<void>;
  onReassign(taskId: string, runtime: string, model?: string | null): Promise<boolean>;
  onSelectTask(taskId: string): Promise<void>;
}

export function TaskDetailPane({
  detail,
  loadingTaskId,
  actionPending,
  capabilities,
  onRetry,
  onApprove,
  onReject,
  onReopen,
  onReassign,
  onSelectTask
}: TaskDetailPaneProps) {
  const [runtimeSelection, setRuntimeSelection] = useState("");
  const [modelSelection, setModelSelection] = useState("");
  const [activeTab, setActiveTab] = useState<DetailTab>("progress");
  const latestRun = detail?.runs[detail.runs.length - 1] ?? null;
  const latestJanitor = detail?.janitorResults[detail.janitorResults.length - 1] ?? null;
  const recentEvents = detail ? [...detail.events].sort((left, right) => right.createdAt.localeCompare(left.createdAt)).slice(0, 10) : [];
  const recentLogs = detail ? detail.logs.slice(-16) : [];
  const latestLog = recentLogs.length > 0 ? recentLogs[recentLogs.length - 1] : null;
  const latestEvent = recentEvents[0] ?? null;
  const latestSignalAt =
    latestLog?.createdAt ?? latestEvent?.createdAt ?? latestRun?.startedAt ?? detail?.task.updatedAt ?? new Date().toISOString();
  const staleRunning = Boolean(detail?.task.status === "running" && isStaleSignal(latestSignalAt));
  const availableActions = useMemo(() => (detail ? resolveActions(detail.task.status) : []), [detail]);
  const actionDisabled = Boolean(detail && (loadingTaskId === detail.task.id || actionPending));

  useEffect(() => {
    setRuntimeSelection("");
    setModelSelection("");
    setActiveTab(detail?.task.status === "review" || detail?.task.status === "done" ? "review" : "progress");
  }, [detail?.task.id, detail?.task.status]);

  const runtimeOptions = capabilities.map((capability) => capability.runtime);
  const selectedCapability = capabilities.find((capability) => capability.runtime === runtimeSelection) ?? null;

  const staleWhileLoading = Boolean(loadingTaskId && loadingTaskId !== detail?.task.id);

  if (staleWhileLoading) {
    return (
      <section className="panel detail-panel empty-state" id="task-detail">
        <p>Loading selected task detail…</p>
      </section>
    );
  }

  if (!detail) {
    return (
      <section className="panel detail-panel empty-state" id="task-detail">
        <p>Select a task to inspect live progress, deterministic review, and routing detail in one place.</p>
      </section>
    );
  }

  const { task } = detail;

  return (
    <section className="panel detail-panel" id="task-detail">
      <div className="detail-hero">
        <div>
          <p className="eyebrow">Selected Task</p>
          <h2>{task.title}</h2>
          <p className="detail-copy">
            {describeTaskState(task.status, task.chosenRuntime)}
          </p>
          <div className="detail-chip-row">
            <span className={`badge ${task.status === "failed" || task.status === "blocked" ? "warn" : task.status === "running" ? "ok" : "neutral"}`}>
              {task.status}
            </span>
            <span className="badge neutral">{task.role}</span>
            <span className="badge neutral">{task.taskType}</span>
            <span className="badge neutral">{agentTopologyLabel(task.agentMode, detail.children.length)}</span>
            <span className={`badge band-${task.tokenBudget.headroomBand}`}>{task.tokenBudget.headroomBand}</span>
          </div>
        </div>

        <div className="detail-actions">
          {availableActions.includes("retry") ? (
            <button type="button" disabled={actionDisabled} onClick={() => void onRetry(task.id)}>
              Retry
            </button>
          ) : null}
          {availableActions.includes("approve") ? (
            <button type="button" disabled={actionDisabled} onClick={() => void onApprove(task.id)}>
              Approve
            </button>
          ) : null}
          {availableActions.includes("reject") ? (
            <button type="button" disabled={actionDisabled} onClick={() => void onReject(task.id)}>
              Reject
            </button>
          ) : null}
          {availableActions.includes("reopen") ? (
            <button type="button" disabled={actionDisabled} onClick={() => void onReopen(task.id)}>
              Reopen
            </button>
          ) : null}
        </div>
      </div>

      <div className="detail-summary-grid">
        <div className="summary-card">
          <span>Runtime</span>
          <strong>{task.chosenRuntime ?? "pending"}</strong>
          <p>{task.chosenProvider ?? "provider pending"} · {task.chosenModel ?? "model pending"}</p>
        </div>
        <div className="summary-card">
          <span>Session</span>
          <strong>{detail.session?.status ?? "none"}</strong>
          <p>{detail.session?.externalSessionId ?? "local session"}</p>
        </div>
        <div className="summary-card">
          <span>Run</span>
          <strong>{latestRun?.status ?? "none"}</strong>
          <p>{latestRun?.summary ?? "no run yet"}</p>
        </div>
        <div className="summary-card">
          <span>Monitoring</span>
          <strong>{staleRunning ? "stalled" : "healthy"}</strong>
          <p>
            last signal {formatTimeAgo(latestSignalAt)} · {latestRun ? runDurationLabel(latestRun.startedAt) : "no active run"}
          </p>
        </div>
        <div className="summary-card">
          <span>Graph</span>
          <strong>{detail.dependencies.length + detail.children.length}</strong>
          <p>{detail.dependencies.length} deps · {detail.children.length} children</p>
        </div>
      </div>

      {latestLog || latestEvent ? (
        <div className={`progress-signal prominent ${staleRunning ? "warn-signal" : ""}`}>
          <span>{latestLog ? latestLog.stream : "latest event"}</span>
          <strong>
            {latestLog
              ? latestLog.message.trim().slice(0, 240)
              : latestEvent
                ? summarizeEvent(latestEvent)
                : ""}
          </strong>
        </div>
      ) : null}

      <div className="detail-tabs" role="tablist" aria-label="Task detail views">
        {(["progress", "review", "route"] as DetailTab[]).map((tab) => (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={activeTab === tab}
            className={`detail-tab ${activeTab === tab ? "active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {DETAIL_TAB_LABELS[tab]}
          </button>
        ))}
      </div>

      <div className="detail-tab-panel">
        {activeTab === "progress" ? (
          <>
            <div className="detail-section">
              <div className="section-header-row">
                <h3>Progress Timeline</h3>
                <span className={`badge ${staleRunning ? "warn" : "neutral"}`}>
                  {recentEvents.length} events · signal {formatTimeAgo(latestSignalAt)}
                </span>
              </div>
              <div className="progress-timeline">
                {recentEvents.length > 0 ? (
                  recentEvents.map((event) => (
                    <div key={event.id} className="event-row progress-row">
                      <strong>{summarizeEvent(event)}</strong>
                      <p>{formatTimestamp(event.createdAt)}</p>
                    </div>
                  ))
                ) : (
                  <p className="detail-copy">No progress events recorded yet.</p>
                )}
              </div>
            </div>

            <div className="detail-section">
              <div className="section-header-row">
                <h3>Worker Output</h3>
                <span className="badge neutral">{recentLogs.length} lines</span>
              </div>
              <div className="log-box">
                {recentLogs.length > 0 ? (
                  recentLogs.map((log) => <pre key={log.id}>{`[${log.stream}] ${log.message}`}</pre>)
                ) : (
                  <p>No logs yet.</p>
                )}
              </div>
            </div>
          </>
        ) : null}

        {activeTab === "review" ? (
          <>
            <div className="detail-section">
              <h3>Verification</h3>
              <div className="diff-box">{latestJanitor?.diffSummary ?? "Diff summary unavailable."}</div>
              <ul className="detail-list compact-list">
                {latestJanitor?.checks.length
                  ? latestJanitor.checks.map((check) => (
                      <li key={`${check.type}-${check.label}`}>
                        {check.label}: {check.status}
                      </li>
                    ))
                  : [<li key="no-janitor">No janitor result yet.</li>]}
              </ul>
            </div>

            <div className="detail-section">
              <h3>Diff</h3>
              <div className="log-box">
                {detail.diffText ? <pre>{detail.diffText}</pre> : <p>No diff available for this task yet.</p>}
              </div>
            </div>

            <div className="detail-section">
              <h3>Review Decisions</h3>
              <ul className="detail-list compact-list">
                {detail.reviews.length
                  ? detail.reviews.map((review) => (
                      <li key={review.id}>
                        {review.decision}: {review.summary}
                      </li>
                    ))
                  : [<li key="no-review">No review decisions yet.</li>]}
              </ul>
            </div>

            <div className="detail-section">
              <h3>Graph Context</h3>
              <ul className="detail-list compact-list">
                {detail.dependencies.length
                  ? detail.dependencies.map((dependency) => (
                      <li key={dependency.id}>
                        <button type="button" className="detail-link-button" onClick={() => void onSelectTask(dependency.id)}>
                          Depends on {dependency.title} ({dependency.status})
                        </button>
                      </li>
                    ))
                  : [<li key="no-deps">No dependencies.</li>]}
              </ul>
              <ul className="detail-list compact-list">
                {detail.children.length
                  ? detail.children.map((child) => (
                      <li key={child.id}>
                        <button type="button" className="detail-link-button" onClick={() => void onSelectTask(child.id)}>
                          Child: {child.title} ({child.status})
                        </button>
                      </li>
                    ))
                  : [<li key="no-children">No child tasks.</li>]}
              </ul>
            </div>
          </>
        ) : null}

        {activeTab === "route" ? (
          <>
            <div className="detail-section">
              <h3>Routing Plan</h3>
              <p>{task.routingRationale?.summary ?? "Routing pending. This task has not been dispatched yet."}</p>
              <ul className="detail-list compact-list">
                <li>Attempts: {task.attempts} / {task.maxAttempts}</li>
                <li>Quota: {detail.session?.quotaState ?? "unknown"}</li>
                <li>Worktree: {detail.worktree?.path ?? "not allocated"}</li>
                <li>Locks: {detail.locks.length}</li>
              </ul>
              {task.routingRationale?.hardGuards.length ? (
                <ul className="detail-list compact-list">
                  {task.routingRationale.hardGuards.map((guard) => (
                    <li key={guard}>{guard}</li>
                  ))}
                </ul>
              ) : null}
            </div>

            <div className="detail-section">
              <h3>Runtime Control</h3>
              <label className="field">
                <span>Reassign runtime</span>
                <select
                  value={runtimeSelection}
                  disabled={actionDisabled}
                  onChange={(event) => setRuntimeSelection(event.target.value)}
                >
                  <option value="">Choose runtime</option>
                  {runtimeOptions.map((runtime) => (
                    <option key={runtime} value={runtime}>
                      {runtime}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Provider / model</span>
                <select
                  value={modelSelection}
                  disabled={!runtimeSelection || actionDisabled}
                  onChange={(event) => setModelSelection(event.target.value)}
                >
                  <option value="">Use router default</option>
                  {selectedCapability?.models.map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                disabled={!runtimeSelection || actionDisabled}
                onClick={async () => {
                  if (!runtimeSelection) {
                    return;
                  }
                  const succeeded = await onReassign(task.id, runtimeSelection, modelSelection || null);
                  if (succeeded) {
                    setRuntimeSelection("");
                    setModelSelection("");
                  }
                }}
              >
                Reassign Task
              </button>
              <ul className="detail-list compact-list">
                <li>Owned files: {task.ownedFiles.length > 0 ? task.ownedFiles.join(", ") : "none"}</li>
                <li>Read-only paths: {task.readOnlyPaths.length > 0 ? task.readOnlyPaths.join(", ") : "none"}</li>
              </ul>
            </div>

            <div className="detail-section">
              <h3>Token Budget</h3>
              <ul className="detail-list compact-list">
                <li>Headroom ratio: {(task.tokenBudget.headroomRatio * 100).toFixed(1)}%</li>
                <li>Prompt tokens: {task.tokenBudget.predictedPromptTokens}</li>
                <li>Output tokens: {task.tokenBudget.predictedOutputTokens}</li>
                <li>Growth tokens: {task.tokenBudget.predictedGrowthTokens}</li>
                <li>Session occupancy: {task.tokenBudget.sessionOccupancyEstimate}</li>
                <li>Accounting tier: {task.tokenBudget.tier}</li>
              </ul>
            </div>
          </>
        ) : null}
      </div>
    </section>
  );
}

function resolveActions(
  status: TaskDetailPayload["task"]["status"]
): Array<"retry" | "approve" | "reject" | "reopen"> {
  switch (status) {
    case "review":
      return ["approve", "reject", "retry"];
    case "failed":
    case "blocked":
      return ["retry", "reopen"];
    case "rejected":
      return ["reopen", "retry"];
    case "done":
      return ["reopen"];
    default:
      return [];
  }
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit"
  }).format(date);
}

function formatTimeAgo(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const deltaSeconds = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000));
  if (deltaSeconds < 60) {
    return `${deltaSeconds}s ago`;
  }
  if (deltaSeconds < 3600) {
    return `${Math.floor(deltaSeconds / 60)}m ago`;
  }
  return `${Math.floor(deltaSeconds / 3600)}h ago`;
}

function runDurationLabel(startedAt: string): string {
  const date = new Date(startedAt);
  if (Number.isNaN(date.getTime())) {
    return "duration unknown";
  }
  const deltaSeconds = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000));
  if (deltaSeconds < 60) {
    return `running ${deltaSeconds}s`;
  }
  if (deltaSeconds < 3600) {
    return `running ${Math.floor(deltaSeconds / 60)}m`;
  }
  return `running ${Math.floor(deltaSeconds / 3600)}h`;
}

function isStaleSignal(value: string): boolean {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return true;
  }
  return Date.now() - date.getTime() > 5 * 60 * 1000;
}

function agentTopologyLabel(mode: TaskDetailPayload["task"]["agentMode"], directChildren: number): string {
  if (mode === "single") {
    return "1 agent";
  }
  if (mode === "read_only_strategist") {
    return "1 planner";
  }
  if (mode === "native_subagents") {
    return "multi-agent runtime";
  }
  if (mode === "orchestrator_subtasks") {
    return directChildren > 0 ? `${directChildren + 1} agents` : "task graph";
  }
  return directChildren > 0 ? `${directChildren + 1} agents` : "hybrid agents";
}

function summarizeEvent(event: EventRecord): string {
  const label = EVENT_LABELS[event.eventType] ?? event.eventType;
  const payload = summarizeEventPayload(event.payload);
  return payload ? `${label} · ${payload}` : label;
}

function summarizeEventPayload(payload: EventRecord["payload"]): string {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return "";
  }

  const record = payload as Record<string, unknown>;
  const parts: string[] = [];
  if (typeof record.runtime === "string") {
    parts.push(record.runtime);
  }
  if (typeof record.provider === "string") {
    parts.push(record.provider);
  }
  if (typeof record.status === "string") {
    parts.push(record.status);
  }
  if (typeof record.reason === "string") {
    parts.push(record.reason);
  }
  return parts.slice(0, 3).join(" · ");
}

function describeTaskState(status: TaskDetailPayload["task"]["status"], runtime: string | null): string {
  switch (status) {
    case "running":
      return `Watching delegated execution in ${runtime ?? "its routed runtime"}.`;
    case "review":
      return "Execution finished. Ready for deterministic checks, diff review, and approval.";
    case "failed":
    case "blocked":
      return "This task needs intervention before it can continue.";
    case "done":
      return "Execution is complete and the result is available for inspection.";
    case "rejected":
      return "The result was rejected and can be reopened or retried.";
    default:
      return `Current state is ${status}.`;
  }
}

const DETAIL_TAB_LABELS: Record<DetailTab, string> = {
  progress: "Progress",
  review: "Review",
  route: "Routing"
};

const EVENT_LABELS: Record<string, string> = {
  "strategist.planned": "Strategist planned",
  "task.started": "Dispatch started",
  "task.spawned": "Session spawned",
  "session.started": "Session live",
  "run.started": "Run started",
  "run.completed": "Run completed",
  "session.completed": "Session completed",
  "task.watchdog": "Runtime watchdog tripped",
  "task.blocked": "Task blocked",
  "task.rejected": "Task rejected",
  "task.completed": "Task completed",
  "task.failed": "Task failed"
};
