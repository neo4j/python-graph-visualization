/**
 * The subset of the anywidget model API the React bindings rely on.
 */
export type LocalModel<T extends Record<string, unknown>> = {
  get<K extends keyof T>(key: K): T[K];
  set<K extends keyof T>(key: K, value: T[K]): void;
  on(event: string, listener: () => void): void;
  off(event: string, listener: () => void): void;
  save_changes(): void;
};

/**
 * A minimal, kernel-less model for the static HTML render path.
 * `set` must still update the in-memory data and notify listeners.
 * State is kept local to the page; nothing is synced back to Python.
 */
export function createLocalModel<T extends Record<string, unknown>>(
  data: Partial<T>
): LocalModel<T> {
  const listeners = new Map<string, Set<() => void>>();

  return {
    get<K extends keyof T>(key: K): T[K] {
      return data[key] as T[K];
    },
    set<K extends keyof T>(key: K, value: T[K]): void {
      data[key] = value;
      listeners.get(`change:${String(key)}`)?.forEach((listener) => listener());
    },
    on(event: string, listener: () => void): void {
      const eventListeners = listeners.get(event) ?? new Set<() => void>();
      eventListeners.add(listener);
      listeners.set(event, eventListeners);
    },
    off(event: string, listener: () => void): void {
      listeners.get(event)?.delete(listener);
    },
    save_changes() {},
  };
}
