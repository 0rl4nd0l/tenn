import type { JsonRecord } from "../../shared/types";

export interface StreamEventEntry {
  id: string;
  event: string;
  data: JsonRecord;
}

interface StreamState {
  entries: StreamEventEntry[];
  nextSequence: number;
  ended: boolean;
  startOffset: number;
  listeners: Set<(entry: StreamEventEntry | null) => void>;
}

export class MemoryStreamBridge {
  private readonly streams = new Map<string, StreamState>();

  constructor(private readonly maxEntries = 256) {}

  hasStream(streamId: string): boolean {
    return this.streams.has(streamId);
  }

  createStream(streamId: string): void {
    this.getOrCreateStream(streamId);
  }

  publish(streamId: string, event: string, data: JsonRecord): StreamEventEntry {
    const stream = this.getOrCreateStream(streamId);
    const entry: StreamEventEntry = {
      id: `${Date.now()}-${stream.nextSequence}`,
      event,
      data
    };
    stream.nextSequence += 1;
    stream.entries.push(entry);
    if (stream.entries.length > this.maxEntries) {
      stream.entries.shift();
      stream.startOffset += 1;
    }
    for (const listener of stream.listeners) {
      listener(entry);
    }
    return entry;
  }

  end(streamId: string): void {
    const stream = this.getOrCreateStream(streamId);
    stream.ended = true;
    for (const listener of stream.listeners) {
      listener(null);
    }
    stream.listeners.clear();
  }

  subscribe(
    streamId: string,
    options: {
      lastEventId?: string | null;
      onEntry: (entry: StreamEventEntry) => void;
      onEnd: () => void;
    }
  ): () => void {
    const stream = this.getOrCreateStream(streamId);
    const replayFrom = resolveReplayIndex(stream.entries, options.lastEventId ?? null);
    for (let index = replayFrom; index < stream.entries.length; index += 1) {
      const entry = stream.entries[index];
      if (entry) {
        options.onEntry(entry);
      }
    }
    if (stream.ended) {
      options.onEnd();
      return () => undefined;
    }

    const listener = (entry: StreamEventEntry | null) => {
      if (entry) {
        options.onEntry(entry);
        return;
      }
      options.onEnd();
    };
    stream.listeners.add(listener);
    return () => {
      stream.listeners.delete(listener);
    };
  }

  private getOrCreateStream(streamId: string): StreamState {
    const existing = this.streams.get(streamId);
    if (existing) {
      return existing;
    }
    const created: StreamState = {
      entries: [],
      nextSequence: 0,
      ended: false,
      startOffset: 0,
      listeners: new Set()
    };
    this.streams.set(streamId, created);
    return created;
  }
}

function resolveReplayIndex(entries: StreamEventEntry[], lastEventId: string | null): number {
  if (!lastEventId) {
    return 0;
  }
  const index = entries.findIndex((entry) => entry.id === lastEventId);
  if (index === -1) {
    return 0;
  }
  return index + 1;
}
