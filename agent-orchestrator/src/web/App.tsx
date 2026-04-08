import { useState } from "react";
import { ExecutionOverview } from "./components/ExecutionOverview";
import { CapabilityStrip } from "./components/CapabilityStrip";
import { HeaderBar } from "./components/HeaderBar";
import { KanbanBoard } from "./components/KanbanBoard";
import { StrategistPane } from "./components/StrategistPane";
import { TaskDetailPane } from "./components/TaskDetailPane";
import { WorkspaceContextPane } from "./components/WorkspaceContextPane";
import { useOrchestratorState } from "./hooks/useOrchestratorState";

type WorkspaceView = "overview" | "board" | "inspect";

export function App() {
  const state = useOrchestratorState();
  const [activeView, setActiveView] = useState<WorkspaceView>("overview");
  const delegatedTasks = state.board?.tasks.filter((task) => task.role !== "strategist" && task.taskType !== "planning") ?? [];
  const hasDelegatedWork = delegatedTasks.length > 0;
  const chatModelOptions =
    state.board?.capabilities.find((capability) => capability.runtime === state.chatRuntime)?.models ?? [];

  if (state.loading) {
    return <main className="app-shell loading">Loading orchestrator…</main>;
  }

  if (state.error && !state.board) {
    return <main className="app-shell loading">Error: {state.error}</main>;
  }

  if (!state.board) {
    return <main className="app-shell loading">No board loaded.</main>;
  }

  return (
    <main className="app-shell">
      <HeaderBar
        board={state.board}
        streamOnline={state.streamOnline}
        onRefresh={state.refresh}
        onDispatchReady={state.dispatchReady}
        onRefreshRuntimes={state.refreshRuntimes}
        activeView={activeView}
        onChangeView={setActiveView}
      />
      {state.error ? (
        <div className="app-banner" role="status">
          <span>{state.error}</span>
          <button type="button" onClick={state.clearError}>
            Dismiss
          </button>
        </div>
      ) : null}
      <div className="workspace-layout">
        <section className="workspace-primary">
          <div
            className={`workspace-main ${
              activeView === "board" ? "board-view" : activeView === "inspect" ? "inspect-view" : "overview-view"
            }`}
          >
            <StrategistPane
              conversation={state.board.conversation}
              hasDelegatedWork={hasDelegatedWork}
              chatSending={state.chatSending}
              chatRuntime={state.chatRuntime}
              chatModel={state.chatModel}
              chatModelOptions={chatModelOptions}
              onChatRuntimeChange={state.setChatRuntime}
              onChatModelChange={state.setChatModel}
              pendingUserMessage={state.pendingUserMessage}
              streamingAssistantMessage={state.streamingAssistantMessage}
              pendingApproval={state.pendingApproval}
              onSend={async (message) => {
                await state.sendChat(message);
                setActiveView("overview");
              }}
            />
            {activeView === "overview" ? (
              hasDelegatedWork ? (
                <ExecutionOverview board={state.board} selectedTaskId={state.selectedTaskId} onSelect={state.selectTask} />
              ) : (
                <section className="panel chat-empty-panel">
                  <div className="chat-empty-copy">
                    <p className="eyebrow">Task Stream</p>
                    <h2>Nothing delegated yet</h2>
                    <p className="activity-copy">
                      Use the main chat normally. If I decide something needs execution, work will appear here automatically.
                    </p>
                  </div>
                </section>
              )
            ) : activeView === "board" ? (
              <KanbanBoard
                tasks={state.board.tasks}
                events={state.board.events}
                selectedTaskId={state.selectedTaskId}
                onSelect={state.selectTask}
              />
            ) : (
              <div className="support-grid">
                <CapabilityStrip capabilities={state.board.capabilities} />
                <WorkspaceContextPane snapshot={state.board.projectSnapshot} />
              </div>
            )}
          </div>

          {activeView === "inspect" ? (
            <section className="panel support-drawer">
              <div className="support-summary">
                <div>
                  <p className="eyebrow">Context</p>
                  <strong>Runtime diagnostics and workspace context</strong>
                </div>
              </div>
              <div className="support-grid">
                <CapabilityStrip capabilities={state.board.capabilities} />
                <WorkspaceContextPane snapshot={state.board.projectSnapshot} />
              </div>
            </section>
          ) : null}
        </section>

        <aside className="detail-rail">
          {hasDelegatedWork ? (
            <TaskDetailPane
              detail={state.detail}
              loadingTaskId={state.detailLoadingTaskId}
              actionPending={state.isTaskActionPending(state.detail?.task.id ?? null)}
              capabilities={state.board.capabilities}
              onRetry={(taskId) => state.action(taskId, "retry")}
              onApprove={(taskId) => state.action(taskId, "approve")}
              onReject={(taskId) => state.action(taskId, "reject")}
              onReopen={(taskId) => state.action(taskId, "reopen")}
              onReassign={state.reassign}
              onSelectTask={state.selectTask}
            />
          ) : (
            <section className="panel detail-panel empty-state quiet-detail-panel" id="task-detail">
              <p className="eyebrow">Task Detail</p>
              <h2>Stay in chat</h2>
              <p className="detail-copy">
                This panel stays quiet until work starts. When that happens, the active task will appear here with logs and controls.
              </p>
            </section>
          )}
        </aside>
      </div>
    </main>
  );
}
