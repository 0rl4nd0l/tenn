import type {
  OwnershipLockRecord,
  QueueMetrics,
  RuntimeId,
  SessionRecord,
  TaskRecord
} from "../../shared/types";

export interface SchedulerOptions {
  maxParallelTasks: number;
  maxParallelReadTasks: number;
}

export class TaskScheduler {
  constructor(private readonly options: SchedulerOptions = { maxParallelTasks: 4, maxParallelReadTasks: 8 }) {}

  selectRunnableTasks(
    tasks: TaskRecord[],
    sessions: SessionRecord[],
    locks: OwnershipLockRecord[]
  ): TaskRecord[] {
    const runningTaskIds = new Set(
      sessions.filter((session) => session.status === "running").map((session) => session.taskId)
    );
    const completedTaskIds = new Set(tasks.filter((task) => task.status === "done").map((task) => task.id));
    const lockedTaskIds = new Set(locks.filter((lock) => lock.status === "active").map((lock) => lock.taskId));

    const ready = tasks
      .filter((task) => task.status === "ready")
      .filter((task) => task.dependencies.every((dependency) => completedTaskIds.has(dependency)))
      .filter((task) => !runningTaskIds.has(task.id))
      .filter((task) => task.attempts < task.maxAttempts)
      .filter((task) => task.ownedFiles.length === 0 || !hasExternalLock(task, locks, lockedTaskIds));

    const runningCount = runningTaskIds.size;
    const capacity = Math.max(0, this.options.maxParallelTasks - runningCount);
    if (capacity === 0) {
      return [];
    }

    const writeTasks = ready.filter((task) => task.ownedFiles.length > 0);
    const readTasks = ready.filter((task) => task.ownedFiles.length === 0);
    const scheduled: TaskRecord[] = [];

    for (const task of writeTasks) {
      if (scheduled.length >= capacity) {
        break;
      }
      scheduled.push(task);
    }

    for (const task of readTasks) {
      if (scheduled.length >= capacity || scheduled.filter((item) => item.ownedFiles.length === 0).length >= this.options.maxParallelReadTasks) {
        break;
      }
      scheduled.push(task);
    }

    return scheduled;
  }

  getRunnableTasks(tasks: TaskRecord[], locks: OwnershipLockRecord[]): TaskRecord[] {
    return this.selectRunnableTasks(tasks, [], locks);
  }

  queueMetrics(tasks: TaskRecord[]): QueueMetrics {
    return {
      readyTasks: tasks.filter((task) => task.status === "ready").length,
      runningTasks: tasks.filter((task) => task.status === "running").length,
      reviewTasks: tasks.filter((task) => task.status === "review").length,
      blockedTasks: tasks.filter((task) => task.status === "blocked").length,
      mergeQueueDepth: tasks.filter((task) => task.status === "review" && task.ownedFiles.length > 0).length
    };
  }

  runtimeLoad(tasks: TaskRecord[]): Record<RuntimeId, number> {
    const runtimes: RuntimeId[] = [
      "codex-local",
      "codex-cloud",
      "claude",
      "gemini",
      "cursor",
      "opencode",
      "generic"
    ];
    return runtimes.reduce<Record<RuntimeId, number>>((accumulator, runtime) => {
      accumulator[runtime] = tasks.filter((task) => task.chosenRuntime === runtime && task.status === "running").length;
      return accumulator;
    }, {} as Record<RuntimeId, number>);
  }
}

export { TaskScheduler as Scheduler };

function hasExternalLock(
  task: TaskRecord,
  locks: OwnershipLockRecord[],
  lockedTaskIds: Set<string>
): boolean {
  return locks.some((lock) => {
    if (lock.status !== "active" || !lockedTaskIds.has(lock.taskId) || lock.taskId === task.id) {
      return false;
    }
    return task.ownedFiles.some((file) => file === lock.pathGlob || file.startsWith(lock.pathGlob.replace(/\*+$/, "")));
  });
}
