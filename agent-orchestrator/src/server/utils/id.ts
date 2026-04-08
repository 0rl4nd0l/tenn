import { randomUUID } from "crypto";

export function makeId(prefix: string): string {
  return `${prefix}_${randomUUID()}`;
}

export const createId = makeId;
