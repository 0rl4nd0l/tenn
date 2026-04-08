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
  const liveRunning = board.tasks.filter((task) => task.status === "running" && liveSessionByTaskId.has(task.id)).length;
  const queuedTasks = board.tasks.filter((task) => task.status === "ready" || task.status === "review").length;
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
          <span className="summary-inline">{queuedTasks} queued</span>
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
