import { BoardState, TaskRecord } from "../../shared/types";

interface ExecutionOverviewProps {
  board: BoardState;
  selectedTaskId: string | null;
  onSelect(taskId: string): Promise<void>;
}

const REVIEW_STATUSES: TaskRecord["status"][] = ["review", "failed", "blocked", "rejected"];

export function ExecutionOverview({ board, selectedTaskId, onSelect }: ExecutionOverviewProps) {
  const sessionByTaskId = new Map(board.sessions.map((session) => [session.taskId, session]));
  const latestSignalByTaskId = buildLatestSignalByTaskId(board);
  const childTaskCountByParentId = buildChildTaskCountByParentId(board.tasks);
  const liveSessionTaskIds = new Set(
    board.sessions
      .filter((session) => session.status === "running" || session.status === "waiting")
      .map((session) => session.taskId)
  );
  const doneCount = board.tasks.filter((task) => task.status === "done").length;
  const reviewCount = board.tasks.filter((task) => task.status === "review").length;
  const stalledRunningCount = board.tasks.filter(
    (task) =>
      task.status === "running" &&
      (!liveSessionTaskIds.has(task.id) || isStaleSignal(latestSignalByTaskId.get(task.id) ?? task.updatedAt))
  ).length;

  const latestPlanTaskId = board.conversation.latestPlanTaskId;
  const fallbackStrategistRoot = board.tasks
    .filter((task) => task.role === "strategist" && !task.parentId)
    .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))[0];
  const planRootTaskId = latestPlanTaskId ?? fallbackStrategistRoot?.id ?? null;
  const planBranchTaskIds = collectBranchTaskIds(board.tasks, planRootTaskId);
  const planBranchTasks = board.tasks.filter((task) => planBranchTaskIds.has(task.id));

  const displayedPlanTasks = (
    planBranchTasks.length > 0
      ? planBranchTasks.filter((task) => ["ready", "running", "review", "backlog"].includes(task.status))
      : board.tasks.filter((task) => task.status === "ready" || task.status === "running" || task.status === "review")
  )
    .filter((task) => planBranchTasks.length > 0 || isRecentOrLive(task.updatedAt) || liveSessionTaskIds.has(task.id))
    .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))
    .slice(0, 5);

  const liveRunningTasks = prioritizeCurrentPlan(
    board.tasks.filter((task) => task.status === "running" && liveSessionTaskIds.has(task.id)),
    planBranchTaskIds
  ).slice(0, 4);

  const staleRunningTasks = prioritizeCurrentPlan(
    board.tasks.filter((task) => task.status === "running" && !liveSessionTaskIds.has(task.id)),
    planBranchTaskIds
  ).slice(0, 4);

  const reviewQueue = prioritizeCurrentPlan(
    board.tasks.filter((task) => REVIEW_STATUSES.includes(task.status) && isRecentOrLive(task.updatedAt)),
    planBranchTaskIds
  ).slice(0, 5);
  const reviewHistory = prioritizeCurrentPlan(
    board.tasks.filter((task) => REVIEW_STATUSES.includes(task.status) && !isRecentOrLive(task.updatedAt)),
    planBranchTaskIds
  ).slice(0, 8);

  return (
    <section className="panel overview-panel">
      <div className="panel-header compact-header">
        <div>
          <p className="eyebrow">Spawned Work</p>
          <h2>Delegated tasks from this chat</h2>
          <p className="activity-copy">
            When the assistant decides to execute, the spawned plan, live runs, and review queue appear here.
          </p>
        </div>
        <div className="overview-meta">
          <span className="badge neutral">{board.tasks.length} tasks</span>
          <span className={`badge ${liveRunningTasks.length > 0 ? "ok" : "warn"}`}>
            {liveRunningTasks.length > 0 ? `${liveRunningTasks.length} live` : "no live session"}
          </span>
          <span className={`badge ${reviewCount > 0 ? "warn" : "ok"}`}>
            {reviewCount > 0 ? `${reviewCount} in review` : "review clear"}
          </span>
          <span className="badge neutral">{doneCount} done</span>
          {stalledRunningCount > 0 ? <span className="badge warn">{stalledRunningCount} stalled</span> : null}
        </div>
      </div>

      <div className="timeline-stack">
        <article className="timeline-lane">
          <div className="timeline-lane-header">
            <div>
              <p className="eyebrow">Plan</p>
              <h3>Current delegation plan</h3>
              <p className="activity-copy">Latest strategist branch or the freshest routed tasks.</p>
            </div>
            <span className="badge neutral">{displayedPlanTasks.length}</span>
          </div>
          {displayedPlanTasks.length > 0 ? (
            <div className="timeline-list">
              {displayedPlanTasks.map((task) => (
                <button
                  key={task.id}
                  type="button"
                  className={`timeline-item ${selectedTaskId === task.id ? "selected" : ""}`}
                  aria-pressed={selectedTaskId === task.id}
                  onClick={() => void onSelect(task.id)}
                >
                  <div className="timeline-item-top">
                    <span className="role-pill">{task.role}</span>
                    <span className={`badge ${planStatusBadgeTone(task, liveSessionTaskIds)}`}>{planStatusLabel(task, liveSessionTaskIds)}</span>
                  </div>
                  <div className="timeline-item-copy">
                    <strong>{task.title}</strong>
                    <p>
                      {task.chosenRuntime ?? "routing pending"} · {freshnessLabel(task.updatedAt, liveSessionTaskIds.has(task.id))}
                    </p>
                  </div>
                  <div className="timeline-item-meta">
                    <span>{task.taskType}</span>
                    <span>{agentTopologyLabel(task, childTaskCountByParentId.get(task.id) ?? 0)}</span>
                    {planBranchTaskIds.has(task.id) ? <span>current plan</span> : <span>cross-plan</span>}
                    {task.dependencies.length > 0 ? <span>{task.dependencies.length} deps</span> : null}
                    {task.attempts > 1 ? <span>attempt {task.attempts}</span> : null}
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <p className="activity-copy">No routed tasks yet.</p>
          )}
        </article>

        <article className="timeline-lane">
          <div className="timeline-lane-header">
            <div>
              <p className="eyebrow">Run</p>
              <h3>Running now</h3>
              <p className="activity-copy">Only live session-backed tasks are shown as active.</p>
            </div>
            <span className={`badge ${liveRunningTasks.length > 0 ? "ok" : "warn"}`}>{liveRunningTasks.length}</span>
          </div>
          {liveRunningTasks.length > 0 ? (
            <div className="timeline-list">
              {liveRunningTasks.map((task) => {
                const session = sessionByTaskId.get(task.id);
                return (
                  <button
                    key={task.id}
                    type="button"
                    className={`timeline-item ${selectedTaskId === task.id ? "selected" : ""}`}
                    aria-pressed={selectedTaskId === task.id}
                    onClick={() => void onSelect(task.id)}
                  >
                    <div className="timeline-item-top">
                      <span className="role-pill">{task.role}</span>
                      <span className="badge ok">live</span>
                    </div>
                    <div className="timeline-item-copy">
                      <strong>{task.title}</strong>
                      <p>
                        {task.chosenRuntime ?? "routing pending"} · {session?.status ?? "running"} · {runDurationLabel(session?.startedAt ?? task.updatedAt)}
                      </p>
                    </div>
                    <div className="timeline-item-meta">
                      <span>{monitorHealthLabel(latestSignalByTaskId.get(task.id) ?? task.updatedAt, true)}</span>
                      <span>{agentTopologyLabel(task, childTaskCountByParentId.get(task.id) ?? 0)}</span>
                      {planBranchTaskIds.has(task.id) ? <span>current plan</span> : <span>cross-plan</span>}
                      {task.attempts > 1 ? <span>attempt {task.attempts}</span> : null}
                    </div>
                  </button>
                );
              })}
            </div>
          ) : (
            <p className="activity-copy">No live execution right now.</p>
          )}
          {staleRunningTasks.length > 0 ? (
            <details>
              <summary className="activity-copy">
                {staleRunningTasks.length} non-live running task{staleRunningTasks.length > 1 ? "s" : ""}
              </summary>
              <div className="timeline-list">
                {staleRunningTasks.map((task) => (
                  <button
                    key={task.id}
                    type="button"
                    className={`timeline-item ${selectedTaskId === task.id ? "selected" : ""}`}
                    aria-pressed={selectedTaskId === task.id}
                    onClick={() => void onSelect(task.id)}
                  >
                    <div className="timeline-item-top">
                      <span className="role-pill">{task.role}</span>
                      <span className="badge warn">no live session</span>
                    </div>
                    <div className="timeline-item-copy">
                      <strong>{task.title}</strong>
                      <p>{task.chosenRuntime ?? "routing pending"} · {monitorHealthLabel(latestSignalByTaskId.get(task.id) ?? task.updatedAt, false)}</p>
                    </div>
                    <div className="timeline-item-meta">
                      <span>needs retry or reopen</span>
                      <span>{agentTopologyLabel(task, childTaskCountByParentId.get(task.id) ?? 0)}</span>
                      {planBranchTaskIds.has(task.id) ? <span>current plan</span> : <span>historical</span>}
                    </div>
                  </button>
                ))}
              </div>
            </details>
          ) : null}
        </article>

        <article className="timeline-lane">
          <div className="timeline-lane-header">
            <div>
              <p className="eyebrow">Review</p>
              <h3>Review queue</h3>
              <p className="activity-copy">Current-plan and recent items are prioritized by default.</p>
            </div>
            <span className="badge neutral">{reviewQueue.length}</span>
          </div>
          {reviewQueue.length > 0 ? (
            <div className="timeline-list">
              {reviewQueue.map((task) => (
                <button
                  key={task.id}
                  type="button"
                  className={`timeline-item ${selectedTaskId === task.id ? "selected" : ""}`}
                  aria-pressed={selectedTaskId === task.id}
                  onClick={() => void onSelect(task.id)}
                >
                  <div className="timeline-item-top">
                    <span className="role-pill">{task.role}</span>
                    <span
                      className={`badge ${task.status === "failed" || task.status === "blocked" ? "warn" : "neutral"}`}
                    >
                      {task.status}
                    </span>
                  </div>
                  <div className="timeline-item-copy">
                    <strong>{task.title}</strong>
                    <p>{task.status} · {task.chosenRuntime ?? "unrouted"} · {freshnessLabel(task.updatedAt, false)}</p>
                  </div>
                  <div className="timeline-item-meta">
                    <span>{agentTopologyLabel(task, childTaskCountByParentId.get(task.id) ?? 0)}</span>
                    {planBranchTaskIds.has(task.id) ? <span>current plan</span> : <span>recent</span>}
                    {task.dependencies.length > 0 ? <span>{task.dependencies.length} deps</span> : null}
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <p className="activity-copy">Nothing waiting for review.</p>
          )}
          {reviewHistory.length > 0 ? (
            <details>
              <summary className="activity-copy">
                Show historical review/failure items ({reviewHistory.length})
              </summary>
              <div className="timeline-list">
                {reviewHistory.map((task) => (
                  <button
                    key={task.id}
                    type="button"
                    className={`timeline-item ${selectedTaskId === task.id ? "selected" : ""}`}
                    aria-pressed={selectedTaskId === task.id}
                    onClick={() => void onSelect(task.id)}
                  >
                    <div className="timeline-item-top">
                      <span className="role-pill">{task.role}</span>
                      <span className={`badge ${task.status === "failed" || task.status === "blocked" ? "warn" : "neutral"}`}>
                        {task.status}
                      </span>
                    </div>
                    <div className="timeline-item-copy">
                      <strong>{task.title}</strong>
                      <p>{task.chosenRuntime ?? "unrouted"} · {freshnessLabel(task.updatedAt, false)}</p>
                    </div>
                    <div className="timeline-item-meta">
                      <span>{agentTopologyLabel(task, childTaskCountByParentId.get(task.id) ?? 0)}</span>
                      <span>historical</span>
                    </div>
                  </button>
                ))}
              </div>
            </details>
          ) : null}
        </article>
      </div>
    </section>
  );
}

function collectBranchTaskIds(tasks: TaskRecord[], rootTaskId: string | null): Set<string> {
  const ids = new Set<string>();
  if (!rootTaskId) {
    return ids;
  }
  ids.add(rootTaskId);
  const byParent = new Map<string, TaskRecord[]>();
  for (const task of tasks) {
    if (!task.parentId) {
      continue;
    }
    const siblings = byParent.get(task.parentId) ?? [];
    siblings.push(task);
    byParent.set(task.parentId, siblings);
  }
  const queue = [rootTaskId];
  while (queue.length > 0) {
    const current = queue.shift();
    if (!current) {
      continue;
    }
    for (const child of byParent.get(current) ?? []) {
      if (ids.has(child.id)) {
        continue;
      }
      ids.add(child.id);
      queue.push(child.id);
    }
  }
  return ids;
}

function prioritizeCurrentPlan(tasks: TaskRecord[], planBranchTaskIds: Set<string>): TaskRecord[] {
  return [...tasks].sort((left, right) => {
    const leftPlan = planBranchTaskIds.has(left.id) ? 0 : 1;
    const rightPlan = planBranchTaskIds.has(right.id) ? 0 : 1;
    if (leftPlan !== rightPlan) {
      return leftPlan - rightPlan;
    }
    return right.updatedAt.localeCompare(left.updatedAt);
  });
}

function isRecentOrLive(updatedAt: string): boolean {
  const stamp = new Date(updatedAt).getTime();
  if (Number.isNaN(stamp)) {
    return false;
  }
  const ageMs = Date.now() - stamp;
  return ageMs <= 6 * 60 * 60 * 1000;
}

function freshnessLabel(updatedAt: string, isLive: boolean): string {
  if (isLive) {
    return "live";
  }
  const stamp = new Date(updatedAt).getTime();
  if (Number.isNaN(stamp)) {
    return `updated ${updatedAt}`;
  }
  const ageMs = Date.now() - stamp;
  if (ageMs <= 30 * 60 * 1000) {
    return `recent · ${formatTimeAgo(updatedAt)}`;
  }
  if (ageMs <= 6 * 60 * 60 * 1000) {
    return `stale · ${formatTimeAgo(updatedAt)}`;
  }
  return `historical · ${formatTimeAgo(updatedAt)}`;
}

function planStatusLabel(task: TaskRecord, liveSessionTaskIds: Set<string>): string {
  if (task.status === "running" && liveSessionTaskIds.has(task.id)) {
    return "live";
  }
  if (task.status === "running" && !liveSessionTaskIds.has(task.id)) {
    return "no live session";
  }
  if (task.status === "ready" || task.status === "backlog") {
    return "queued";
  }
  return task.status;
}

function planStatusBadgeTone(task: TaskRecord, liveSessionTaskIds: Set<string>): "ok" | "warn" | "neutral" {
  if (task.status === "running" && liveSessionTaskIds.has(task.id)) {
    return "ok";
  }
  if (task.status === "running" && !liveSessionTaskIds.has(task.id)) {
    return "warn";
  }
  if (task.status === "ready" || task.status === "backlog") {
    return "neutral";
  }
  return "neutral";
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

function isStaleSignal(value: string): boolean {
  const stamp = new Date(value).getTime();
  if (Number.isNaN(stamp)) {
    return true;
  }
  return Date.now() - stamp > 5 * 60 * 1000;
}

function monitorHealthLabel(lastSignalAt: string, live: boolean): string {
  if (live && !isStaleSignal(lastSignalAt)) {
    return `live · signal ${formatTimeAgo(lastSignalAt)}`;
  }
  if (!isStaleSignal(lastSignalAt)) {
    return `recent signal · ${formatTimeAgo(lastSignalAt)}`;
  }
  return `stalled signal · ${formatTimeAgo(lastSignalAt)}`;
}

function runDurationLabel(startedAt: string): string {
  const stamp = new Date(startedAt).getTime();
  if (Number.isNaN(stamp)) {
    return "duration unknown";
  }
  const durationSeconds = Math.max(0, Math.round((Date.now() - stamp) / 1000));
  if (durationSeconds < 60) {
    return `running ${durationSeconds}s`;
  }
  if (durationSeconds < 3600) {
    return `running ${Math.floor(durationSeconds / 60)}m`;
  }
  return `running ${Math.floor(durationSeconds / 3600)}h`;
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
