import type { OwnershipLockRecord } from "../../shared/types";
import { createId } from "../utils/id";
import { nowIso } from "../utils/time";

export class OwnershipLockManager {
  private readonly locks = new Map<string, OwnershipLockRecord>();

  constructor(initialLocks: OwnershipLockRecord[] = []) {
    for (const lock of initialLocks) {
      this.locks.set(lock.id, lock);
    }
  }

  snapshot(): OwnershipLockRecord[] {
    return [...this.locks.values()];
  }

  findConflicts(taskId: string, paths: string[], mode: "read" | "write"): OwnershipLockRecord[] {
    return [...this.locks.values()].filter((lock) => {
      if (lock.status !== "active" || lock.taskId === taskId) {
        return false;
      }
      const matchesPath = paths.some((target) => pathsOverlap(target, lock.pathGlob));
      if (!matchesPath) {
        return false;
      }
      if (mode === "read" && lock.mode === "read") {
        return false;
      }
      return true;
    });
  }

  acquire(taskId: string, paths: string[], mode: "read" | "write"): OwnershipLockRecord[] {
    const conflicts = this.findConflicts(taskId, paths, mode);
    if (conflicts.length > 0) {
      throw new Error(`lock conflict for ${taskId}: ${conflicts.map((item) => item.pathGlob).join(", ")}`);
    }
    const now = nowIso();
    const created = paths.map<OwnershipLockRecord>((pathGlob) => ({
      id: createId("lock"),
      taskId,
      pathGlob,
      mode,
      status: "active",
      createdAt: now,
      updatedAt: now
    }));
    for (const lock of created) {
      this.locks.set(lock.id, lock);
    }
    return created;
  }

  releaseForTask(taskId: string): OwnershipLockRecord[] {
    const now = nowIso();
    const released: OwnershipLockRecord[] = [];
    for (const [id, lock] of this.locks.entries()) {
      if (lock.taskId === taskId && lock.status === "active") {
        const next = { ...lock, status: "released" as const, updatedAt: now };
        this.locks.set(id, next);
        released.push(next);
      }
    }
    return released;
  }
}

function pathsOverlap(left: string, right: string): boolean {
  const normalizedLeft = normalizeScope(left);
  const normalizedRight = normalizeScope(right);

  return (
    normalizedLeft === normalizedRight ||
    normalizedLeft.startsWith(`${normalizedRight}/`) ||
    normalizedRight.startsWith(`${normalizedLeft}/`) ||
    normalizedLeft.startsWith(normalizedRight) ||
    normalizedRight.startsWith(normalizedLeft)
  );
}

function normalizeScope(scope: string): string {
  return scope.replace(/\/\*\*$/, "").replace(/\*+$/, "").replace(/\/$/, "");
}
