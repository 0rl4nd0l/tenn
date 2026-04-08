import { useEffect, useMemo, useState } from "react";
import { EventRecord, TaskRecord } from "../../shared/types";

const COLUMNS: Array<{
  id: string;
  label: string;
  statuses: TaskRecord["status"][];
}> = [
  { id: "backlog", label: "Backlog", statuses: ["backlog"] },
  { id: "ready", label: "Ready", statuses: ["ready"] },
  { id: "running", label: "Running", statuses: ["running"] },
  { id: "review", label: "Review", statuses: ["review"] },
  { id: "attention", label: "Attention", statuses: ["blocked", "failed", "rejected"] },
  { id: "done", label: "Done", statuses: ["done"] }
];

interface KanbanBoardProps {
  tasks: TaskRecord[];
  events: EventRecord[];
  selectedTaskId: string | null;
  onSelect(taskId: string): Promise<void>;
}

export function KanbanBoard({ tasks, events, selectedTaskId, onSelect }: KanbanBoardProps) {
  const [focusActive, setFocusActive] = useState(() => readBoardPreference("focus-active", false));
  const [hideDone, setHideDone] = useState(() => readBoardPreference("hide-done", false));
  const [hideEmptyLanes, setHideEmptyLanes] = useState(() => readBoardPreference("hide-empty-lanes", false));
  const childTaskCountByParentId = useMemo(() => buildChildTaskCountByParentId(tasks), [tasks]);
  const latestSignalByTaskId = useMemo(() => buildLatestSignalByTaskId(tasks, events), [tasks, events]);

  const latestTaskEvents = useMemo(() => {
    const records = new Map<string, EventRecord>();
    [...events]
      .sort((left, right) => right.createdAt.localeCompare(left.createdAt))
      .forEach((event) => {
        if (event.entityType !== "task" || records.has(event.entityId)) {
          return;
        }
        records.set(event.entityId, event);
      });
    return records;
  }, [events]);

  const columns = useMemo(() => {
    return COLUMNS
      .filter((column) => {
        if (focusActive && (column.id === "backlog" || column.id === "done")) {
          return false;
        }
        if (hideDone && column.id === "done") {
          return false;
        }
        return true;
      })
      .map((column) => ({
        ...column,
        tasks: tasks
          .filter((task) => column.statuses.includes(task.status))
          .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))
      }))
      .filter((column) => !hideEmptyLanes || column.tasks.length > 0);
  }, [focusActive, hideDone, hideEmptyLanes, tasks]);

  const visibleTaskCount = columns.reduce((total, column) => total + column.tasks.length, 0);

  useEffect(() => {
    writeBoardPreference("focus-active", focusActive);
  }, [focusActive]);

  useEffect(() => {
    writeBoardPreference("hide-done", hideDone);
  }, [hideDone]);

  useEffect(() => {
    writeBoardPreference("hide-empty-lanes", hideEmptyLanes);
  }, [hideEmptyLanes]);

  return (
    <section className="panel kanban-panel">
      <div className="panel-header compact-header">
        <div>
          <p className="eyebrow">Board View</p>
          <h2>Delegated task lanes</h2>
        </div>
        <span className="badge neutral">{visibleTaskCount} visible</span>
      </div>

      <div className="kanban-toolbar">
        <div className="toolbar-actions" role="toolbar" aria-label="Board focus controls">
          <button
            type="button"
            className={`filter-chip ${focusActive ? "active" : ""}`}
            aria-pressed={focusActive}
            onClick={() => setFocusActive((current) => !current)}
          >
            Focus active
          </button>
          <button
            type="button"
            className={`filter-chip ${hideDone ? "active" : ""}`}
            aria-pressed={hideDone}
            onClick={() => setHideDone((current) => !current)}
          >
            Hide done
          </button>
          <button
            type="button"
            className={`filter-chip ${hideEmptyLanes ? "active" : ""}`}
            aria-pressed={hideEmptyLanes}
            onClick={() => setHideEmptyLanes((current) => !current)}
          >
            Hide empty lanes
          </button>
        </div>
        <p className="activity-copy">Use lane inspection when you need queue-level routing visibility beyond the overview timeline.</p>
      </div>

      <div className="kanban-grid">
        {columns.length > 0 ? (
          columns.map((column) => (
            <section key={column.id} className={`kanban-column ${column.id === "attention" ? "attention-column" : ""}`}>
              <div className="kanban-column-header">
                <h3>{column.label}</h3>
                <span>{column.tasks.length}</span>
              </div>

              <div className="kanban-stack">
                {column.tasks.length > 0 ? (
                  column.tasks.map((task) => (
                    <button
                      key={task.id}
                      type="button"
                      aria-pressed={selectedTaskId === task.id}
                      className={`task-card ${selectedTaskId === task.id ? "selected" : ""} ${
                        task.status === "running" ? "live" : ""
                      } ${task.status === "running" && isStaleSignal(latestSignalByTaskId.get(task.id) ?? task.updatedAt) ? "stalled" : ""}`}
                      onClick={() => void onSelect(task.id)}
                    >
                      <div className="task-card-top">
                        <span className="role-pill">{task.role}</span>
                        <span className={`badge ${task.status === "failed" || task.status === "blocked" ? "warn" : "neutral"}`}>
                          {task.status}
                        </span>
                      </div>
                      <strong>{task.title}</strong>
                      <p>{summarizeBody(task, latestTaskEvents.get(task.id))}</p>
                      <div className="task-card-health">
                        <span>{agentTopologyLabel(task, childTaskCountByParentId.get(task.id) ?? 0)}</span>
                        {task.status === "running" ? (
                          <strong>{runningSignalLabel(latestSignalByTaskId.get(task.id) ?? task.updatedAt)}</strong>
                        ) : (
                          <strong>{formatTimeAgo(latestSignalByTaskId.get(task.id) ?? task.updatedAt)}</strong>
                        )}
                      </div>
                      {latestTaskEvents.get(task.id) ? (
                        <div className="task-card-signal">
                          <span>{summarizeEventType(latestTaskEvents.get(task.id)?.eventType ?? "")}</span>
                          <strong>{formatTimeAgo(latestTaskEvents.get(task.id)?.createdAt ?? task.updatedAt)}</strong>
                        </div>
                      ) : null}
                      <div className="task-card-meta">
                        <span>{task.chosenRuntime ?? "routing pending"}</span>
                        <span>{task.taskType}</span>
                        {task.dependencies.length > 0 ? <span>{task.dependencies.length} deps</span> : null}
                        {task.attempts > 1 ? <span>attempt {task.attempts}</span> : null}
                      </div>
                    </button>
                  ))
                ) : (
                  <div className="kanban-empty">No tasks.</div>
                )}
              </div>
            </section>
          ))
        ) : (
          <div className="kanban-empty">No tasks match the current board filters.</div>
        )}
      </div>
    </section>
  );
}

function summarizeBody(task: TaskRecord, event?: EventRecord): string {
  if (event && ["running", "review", "failed", "blocked"].includes(task.status)) {
    return summarizeEventType(event.eventType);
  }
  return summarizeDescription(task.description);
}

function summarizeDescription(description: string): string {
  const normalized = description.replace(/\s+/g, " ").trim();
  if (normalized.length <= 110) {
    return normalized;
  }
  return `${normalized.slice(0, 107).trim()}...`;
}

function summarizeEventType(eventType: string): string {
  return EVENT_LABELS[eventType] ?? eventType.replace(/\./g, " ");
}

function buildChildTaskCountByParentId(tasks: TaskRecord[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const task of tasks) {
    if (!task.parentId) {
      continue;
    }
    counts.set(task.parentId, (counts.get(task.parentId) ?? 0) + 1);
  }
  return counts;
}

function buildLatestSignalByTaskId(tasks: TaskRecord[], events: EventRecord[]): Map<string, string> {
  const latest = new Map<string, string>();
  for (const task of tasks) {
    latest.set(task.id, task.updatedAt);
  }

  for (const event of events) {
    if (event.entityType !== "task") {
      continue;
    }
    const current = latest.get(event.entityId);
    if (!current || event.createdAt > current) {
      latest.set(event.entityId, event.createdAt);
    }
  }
  return latest;
}

function isStaleSignal(value: string): boolean {
  const stamp = new Date(value).getTime();
  if (Number.isNaN(stamp)) {
    return true;
  }
  return Date.now() - stamp > 5 * 60 * 1000;
}

function runningSignalLabel(signalAt: string): string {
  if (isStaleSignal(signalAt)) {
    return `stalled · ${formatTimeAgo(signalAt)}`;
  }
  return `active · ${formatTimeAgo(signalAt)}`;
}

function agentTopologyLabel(task: TaskRecord, directChildren: number): string {
  if (task.agentMode === "single") {
    return "1 agent";
  }
  if (task.agentMode === "read_only_strategist") {
    return "1 planner";
  }
  if (task.agentMode === "native_subagents") {
    return "multi-agent runtime";
  }
  if (task.agentMode === "orchestrator_subtasks") {
    return directChildren > 0 ? `${directChildren + 1} agents` : "task graph";
  }
  return directChildren > 0 ? `${directChildren + 1} agents` : "hybrid agents";
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

const EVENT_LABELS: Record<string, string> = {
  "strategist.planned": "Planned by strategist",
  "task.started": "Dispatch started",
  "task.spawned": "Session spawned",
  "session.started": "Session live",
  "run.started": "Run started",
  "run.completed": "Run completed",
  "session.completed": "Session completed",
  "task.watchdog": "Runtime watchdog",
  "task.blocked": "Task blocked",
  "task.rejected": "Task rejected",
  "task.completed": "Task completed",
  "task.failed": "Task failed"
};

function readBoardPreference(key: string, fallback: boolean): boolean {
  if (typeof window === "undefined") {
    return fallback;
  }
  const raw = window.localStorage.getItem(`board:${key}`);
  if (raw === "true") {
    return true;
  }
  if (raw === "false") {
    return false;
  }
  return fallback;
}

function writeBoardPreference(key: string, value: boolean): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(`board:${key}`, String(value));
}
