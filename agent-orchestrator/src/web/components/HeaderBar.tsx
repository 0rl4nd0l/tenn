import { BoardState } from "../../shared/types";

type WorkspaceView = "overview" | "board" | "inspect";

interface HeaderBarProps {
  board: BoardState;
  streamOnline: boolean;
  onRefresh(): Promise<void>;
  onDispatchReady(): Promise<void>;
  onRefreshRuntimes(): Promise<void>;
  activeView: WorkspaceView;
  onChangeView(view: WorkspaceView): void;
}

export function HeaderBar({
  board,
  streamOnline,
  onRefresh,
  onDispatchReady,
  onRefreshRuntimes,
  activeView,
  onChangeView
}: HeaderBarProps) {
  const liveSessionByTaskId = new Set(
    board.sessions
      .filter((session) => session.status === "running" || session.status === "waiting")
      .map((session) => session.taskId)
  );
  const latestSignalByTaskId = buildLatestSignalByTaskId(board);
  const liveRunning = board.tasks.filter((task) => task.status === "running" && liveSessionByTaskId.has(task.id)).length;
  const readyQueue = board.tasks.filter((task) => task.status === "ready" || task.status === "backlog").length;
  const reviewQueue = board.tasks.filter((task) => task.status === "review").length;
  const doneTasks = board.tasks.filter((task) => task.status === "done").length;
  const stalledRunning = board.tasks.filter(
    (task) =>
      task.status === "running" &&
      (!liveSessionByTaskId.has(task.id) || isStaleSignal(latestSignalByTaskId.get(task.id) ?? task.updatedAt))
  ).length;
  const attention = board.tasks.filter((task) => ["blocked", "failed", "rejected"].includes(task.status)).length;
  const liveSessions = board.sessions.filter((session) => session.status === "running" || session.status === "waiting").length;

  return (
    <header className="topbar panel">
      <div className="topbar-copy-block">
        <p className="eyebrow">Dark Workspace</p>
        <h1>Agent Orchestrator</h1>
        <p className="topbar-copy">
          Chat first. Delegated work appears only when the assistant decides execution is needed.
        </p>
      </div>

      <div className="topbar-status">
        <div className="topbar-summary compact-summary">
          <span className={`badge ${streamOnline ? "ok" : "warn"}`}>
            {streamOnline ? `live · ${liveSessions} sessions` : "polling fallback"}
          </span>
          <span className="summary-inline">{liveRunning} running</span>
          <span className="summary-inline">{readyQueue} queued</span>
          <span className="summary-inline">{reviewQueue} review</span>
          <span className="summary-inline">{doneTasks} done</span>
          {stalledRunning > 0 ? <span className="summary-inline warning-inline">{stalledRunning} stalled</span> : null}
          <span className="summary-inline">{attention} attention</span>
        </div>
        <div className="view-switch" role="tablist" aria-label="Workspace views">
          <button
            type="button"
            role="tab"
            aria-selected={activeView === "overview"}
            className={`view-switch-button ${activeView === "overview" ? "active" : ""}`}
            onClick={() => onChangeView("overview")}
          >
            Chat
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeView === "board"}
            className={`view-switch-button ${activeView === "board" ? "active" : ""}`}
            onClick={() => onChangeView("board")}
          >
            Board
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeView === "inspect"}
            className={`view-switch-button ${activeView === "inspect" ? "active" : ""}`}
            onClick={() => onChangeView("inspect")}
          >
            Context
          </button>
        </div>
      </div>

      <div className="topbar-actions">
        <button type="button" className="hero-action" onClick={() => void onRefresh()}>
          Refresh
        </button>
        <button type="button" className="hero-action" onClick={() => void onDispatchReady()}>
          Run Ready
        </button>
        <button type="button" className="hero-action" onClick={() => void onRefreshRuntimes()}>
          Probe Runtimes
        </button>
      </div>
    </header>
  );
}

function buildLatestSignalByTaskId(board: BoardState): Map<string, string> {
  const latest = new Map<string, string>();
  for (const task of board.tasks) {
    latest.set(task.id, task.updatedAt);
  }

  const runTaskById = new Map(board.runs.map((run) => [run.id, run.taskId]));
  const sessionTaskById = new Map(board.sessions.map((session) => [session.id, session.taskId]));

  for (const event of board.events) {
    let taskId: string | null = null;
    if (event.entityType === "task") {
      taskId = event.entityId;
    } else if (event.entityType === "run") {
      taskId = runTaskById.get(event.entityId) ?? null;
    } else if (event.entityType === "session") {
      taskId = sessionTaskById.get(event.entityId) ?? null;
    }
    if (!taskId) {
      continue;
    }
    const current = latest.get(taskId);
    if (!current || event.createdAt > current) {
      latest.set(taskId, event.createdAt);
    }
  }

  return latest;
}

function isStaleSignal(timestamp: string): boolean {
  const value = new Date(timestamp).getTime();
  if (Number.isNaN(value)) {
    return true;
  }
  return Date.now() - value > 5 * 60 * 1000;
}
