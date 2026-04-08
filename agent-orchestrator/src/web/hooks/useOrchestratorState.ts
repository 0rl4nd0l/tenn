import { useEffect, useMemo, useRef, useState } from "react";
import { BoardState, StrategistResponse, TaskDetailPayload, TaskRecord } from "../../shared/types";
import { api } from "../api";

interface State {
  board: BoardState | null;
  detail: TaskDetailPayload | null;
  detailLoadingTaskId: string | null;
  selectedTaskId: string | null;
  loading: boolean;
  error: string | null;
  streamOnline: boolean;
  sendChat(message: string): Promise<void>;
  selectTask(taskId: string | null): Promise<void>;
  action(taskId: string, kind: "retry" | "approve" | "reject" | "reopen", runtime?: string): Promise<void>;
  reassign(taskId: string, runtime: string): Promise<boolean>;
  refresh(): Promise<void>;
  dispatchReady(): Promise<void>;
  refreshRuntimes(): Promise<void>;
  clearError(): void;
  isTaskActionPending(taskId: string | null): boolean;
}

export function useOrchestratorState(): State {
  const [board, setBoard] = useState<BoardState | null>(null);
  const [detail, setDetail] = useState<TaskDetailPayload | null>(null);
  const [detailLoadingTaskId, setDetailLoadingTaskId] = useState<string | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [streamOnline, setStreamOnline] = useState(false);
  const [socketGeneration, setSocketGeneration] = useState(0);
  const [taskActionCounts, setTaskActionCounts] = useState<Record<string, number>>({});
  const taskActionCountsRef = useRef<Record<string, number>>({});
  const selectedTaskIdRef = useRef<string | null>(null);
  const detailRequestGenerationRef = useRef(0);

  const focusTaskDetail = () => {
    if (!window.matchMedia("(max-width: 1180px)").matches) {
      return;
    }
    window.requestAnimationFrame(() => {
      document.getElementById("task-detail")?.scrollIntoView({
        behavior: "smooth",
        block: "start"
      });
    });
  };

  const beginTaskAction = (taskId: string) => {
    const next = {
      ...taskActionCountsRef.current,
      [taskId]: (taskActionCountsRef.current[taskId] ?? 0) + 1
    };
    taskActionCountsRef.current = next;
    setTaskActionCounts(next);
  };

  const finishTaskAction = (taskId: string) => {
    const next = { ...taskActionCountsRef.current };
    const remaining = (next[taskId] ?? 0) - 1;
    if (remaining > 0) {
      next[taskId] = remaining;
    } else {
      delete next[taskId];
    }
    taskActionCountsRef.current = next;
    setTaskActionCounts(next);
  };

  const runTaskAction = async (taskId: string, action: () => Promise<boolean | void>): Promise<boolean> => {
    if ((taskActionCountsRef.current[taskId] ?? 0) > 0) {
      return false;
    }
    beginTaskAction(taskId);
    try {
      const result = await action();
      return result !== false;
    } catch (error) {
      setError(toErrorMessage(error));
      return false;
    } finally {
      finishTaskAction(taskId);
    }
  };

  const hydrateBoard = async (next: BoardState, preferredTaskId?: string | null): Promise<boolean> => {
    setBoard(next);
    const nextSelectedTaskId = resolveSelectedTask(next, preferredTaskId ?? selectedTaskId);
    if (nextSelectedTaskId !== selectedTaskId) {
      setSelectedTaskId(nextSelectedTaskId);
    }
    if (nextSelectedTaskId) {
      await loadTaskDetail(nextSelectedTaskId, { showLoading: detail?.task.id !== nextSelectedTaskId });
      return true;
    }
    setDetailLoadingTaskId(null);
    setDetail(null);
    return true;
  };

  const loadTaskDetail = async (taskId: string, options?: { showLoading?: boolean }) => {
    const requestGeneration = detailRequestGenerationRef.current + 1;
    const showLoading = options?.showLoading ?? true;
    detailRequestGenerationRef.current = requestGeneration;
    if (showLoading) {
      setDetailLoadingTaskId(taskId);
    }
    try {
      const payload = await api.getTask(taskId);
      if (detailRequestGenerationRef.current !== requestGeneration) {
        return;
      }
      setDetail(payload);
    } catch (error) {
      if (detailRequestGenerationRef.current !== requestGeneration) {
        return;
      }
      setDetail(null);
      setError(toErrorMessage(error));

      if (!board || board.tasks.some((task) => task.id === taskId)) {
        return;
      }

      const nextSelectedTaskId = resolveSelectedTask(board, selectedTaskIdRef.current === taskId ? null : selectedTaskIdRef.current);
      if (!nextSelectedTaskId || nextSelectedTaskId === taskId) {
        setSelectedTaskId(null);
        return;
      }

      setSelectedTaskId(nextSelectedTaskId);
      await loadTaskDetail(nextSelectedTaskId, { showLoading: true });
    } finally {
      if (showLoading && detailRequestGenerationRef.current === requestGeneration) {
        setDetailLoadingTaskId(null);
      }
    }
  };

  const refreshBoard = async (preferredTaskId?: string | null): Promise<boolean> => {
    try {
      const next = await api.getBoard();
      await hydrateBoard(next, preferredTaskId);
      return true;
    } catch (error) {
      setError(toErrorMessage(error));
      return false;
    }
  };

  useEffect(() => {
    selectedTaskIdRef.current = selectedTaskId;
  }, [selectedTaskId]);

  useEffect(() => {
    void (async () => {
      try {
        await refreshBoard();
      } catch (nextError) {
        setError((nextError as Error).message);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${protocol}://${window.location.host}/ws`);
    let reconnectTimer: number | null = null;
    let reconnectScheduled = false;
    const scheduleReconnect = () => {
      if (reconnectScheduled) {
        return;
      }
      reconnectScheduled = true;
      reconnectTimer = window.setTimeout(() => {
        setSocketGeneration((current) => current + 1);
      }, 3000);
    };
    socket.onopen = () => {
      setStreamOnline(true);
      setError((current) => (current === "Live refresh degraded. Using polling fallback." ? null : current));
    };
    socket.onmessage = () => {
      void refreshBoard(selectedTaskIdRef.current);
    };
    socket.onerror = () => {
      setStreamOnline(false);
      setError((current) => current ?? "Live refresh degraded. Using polling fallback.");
      scheduleReconnect();
    };
    socket.onclose = () => {
      setStreamOnline(false);
      setError((current) => current ?? "Live refresh degraded. Using polling fallback.");
      scheduleReconnect();
    };
    return () => {
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
      }
      socket.close();
    };
  }, [socketGeneration]);

  useEffect(() => {
    if (!board) {
      return;
    }
    const shouldPoll =
      !streamOnline ||
      board.tasks.some((task) => task.status === "running") ||
      board.sessions.some((session) => session.status === "running" || session.status === "waiting");
    if (!shouldPoll) {
      return;
    }
    const timer = window.setInterval(() => {
      void refreshBoard(selectedTaskId);
    }, 2500);
    return () => window.clearInterval(timer);
  }, [board, selectedTaskId, streamOnline]);

  return useMemo(
    () => ({
      board,
      detail,
      detailLoadingTaskId,
      selectedTaskId,
      loading,
      error,
      streamOnline,
      async sendChat(message: string) {
        setError(null);
        try {
          const response = await api.sendChat(message);
          const next = await api.getBoard();
          const preferredTaskId = resolveDelegatedTaskId(next.tasks, response);
          const hydrated = await hydrateBoard(next, preferredTaskId);
          if (hydrated && preferredTaskId) {
            focusTaskDetail();
          }
        } catch (error) {
          setError(toErrorMessage(error));
        }
      },
      async selectTask(taskId: string | null) {
        setError(null);
        try {
          setSelectedTaskId(taskId);
          if (!taskId) {
            detailRequestGenerationRef.current += 1;
            setDetailLoadingTaskId(null);
            setDetail(null);
            return;
          }
          await loadTaskDetail(taskId, { showLoading: true });
          focusTaskDetail();
        } catch (error) {
          setError(toErrorMessage(error));
        }
      },
      async action(taskId: string, kind: "retry" | "approve" | "reject" | "reopen") {
        setError(null);
        await runTaskAction(taskId, async () => {
          if (kind === "retry") {
            await api.retryTask(taskId);
          } else if (kind === "approve") {
            await api.approveTask(taskId);
          } else if (kind === "reject") {
            await api.rejectTask(taskId);
          } else {
            await api.reopenTask(taskId);
          }
          return refreshBoard(selectedTaskId);
        });
      },
      async reassign(taskId: string, runtime: string) {
        setError(null);
        return runTaskAction(taskId, async () => {
          await api.reassignTask(taskId, runtime);
          return refreshBoard(selectedTaskId);
        });
      },
      async refresh() {
        setError(null);
        await refreshBoard(selectedTaskId);
      },
      async dispatchReady() {
        setError(null);
        try {
          await api.tick();
          await refreshBoard(selectedTaskId);
        } catch (error) {
          setError(toErrorMessage(error));
        }
      },
      async refreshRuntimes() {
        setError(null);
        try {
          await api.refreshRuntimes();
          await refreshBoard(selectedTaskId);
        } catch (error) {
          setError(toErrorMessage(error));
        }
      },
      clearError() {
        setError(null);
      },
      isTaskActionPending(taskId: string | null) {
        return Boolean(taskId && (taskActionCountsRef.current[taskId] ?? 0) > 0);
      }
    }),
    [board, detail, detailLoadingTaskId, loading, error, selectedTaskId, streamOnline, taskActionCounts]
  );
}

function resolveDelegatedTaskId(tasks: TaskRecord[], response: StrategistResponse): string | null {
  const statusPriority: Record<TaskRecord["status"], number> = {
    running: 0,
    failed: 1,
    review: 2,
    blocked: 3,
    ready: 4,
    backlog: 5,
    done: 6,
    rejected: 7
  };
  const createdChildren = response.createdTaskIds
    .filter((taskId) => taskId !== response.rootTaskId)
    .map((taskId) => tasks.find((task) => task.id === taskId))
    .filter((task): task is TaskRecord => Boolean(task))
    .sort((left, right) => statusPriority[left.status] - statusPriority[right.status]);
  return createdChildren[0]?.id ?? response.rootTaskId ?? null;
}

function resolvePreferredTaskId(tasks: TaskRecord[], taskId?: string | null): string | null {
  if (!taskId) {
    return null;
  }
  return tasks.some((task) => task.id === taskId) ? taskId : null;
}

function resolveSelectedTask(board: BoardState, preferredTaskId?: string | null): string | null {
  return (
    resolvePreferredTaskId(board.tasks, preferredTaskId) ??
    resolveLatestPlanScopedTaskId(board) ??
    resolveFreshTaskId(board) ??
    board.tasks[0]?.id ??
    null
  );
}

function toErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function resolveLatestPlanScopedTaskId(board: BoardState): string | null {
  const planRootTaskId = board.conversation.latestPlanTaskId;
  if (!planRootTaskId) {
    return null;
  }

  const byParent = new Map<string, TaskRecord[]>();
  for (const task of board.tasks) {
    if (!task.parentId) {
      continue;
    }
    const siblings = byParent.get(task.parentId) ?? [];
    siblings.push(task);
    byParent.set(task.parentId, siblings);
  }

  const stack = [planRootTaskId];
  const branchTasks: TaskRecord[] = [];
  while (stack.length > 0) {
    const current = stack.pop();
    if (!current) {
      continue;
    }
    const children = byParent.get(current) ?? [];
    for (const child of children) {
      branchTasks.push(child);
      stack.push(child.id);
    }
  }

  if (branchTasks.length === 0) {
    return resolvePreferredTaskId(board.tasks, planRootTaskId);
  }

  const priority: Record<TaskRecord["status"], number> = {
    running: 0,
    review: 1,
    ready: 2,
    backlog: 3,
    failed: 4,
    blocked: 5,
    rejected: 6,
    done: 7
  };

  branchTasks.sort((left, right) => {
    const delta = priority[left.status] - priority[right.status];
    if (delta !== 0) {
      return delta;
    }
    return right.updatedAt.localeCompare(left.updatedAt);
  });

  return branchTasks[0]?.id ?? null;
}

function resolveFreshTaskId(board: BoardState): string | null {
  const liveSessionTaskIds = new Set(
    board.sessions
      .filter((session) => session.status === "running" || session.status === "waiting")
      .map((session) => session.taskId)
  );
  const sortedTasks = [...board.tasks].sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
  return (
    sortedTasks.find((task) => task.status === "running" && liveSessionTaskIds.has(task.id))?.id ??
    sortedTasks.find((task) => task.status === "ready" || task.status === "review")?.id ??
    sortedTasks.find((task) => task.status !== "done" && task.status !== "rejected")?.id ??
    sortedTasks[0]?.id ??
    null
  );
}
