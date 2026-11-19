/** Never retain private workspace preferences across a principal change. */
export interface KeyStorage {
  readonly length: number;
  key(index: number): string | null;
  removeItem(key: string): void;
}

const privatePrefixes = ["axiom:workspace:", "axiom:private:"] as const;

export function clearPrivateState(storage: KeyStorage): void {
  const toRemove: string[] = [];
  for (let index = 0; index < storage.length; index += 1) {
    const key = storage.key(index);
    if (key && privatePrefixes.some((prefix) => key.startsWith(prefix))) {
      toRemove.push(key);
    }
  }
  toRemove.forEach((key) => storage.removeItem(key));
}

/** A browser storage error must not interrupt sign-out or private navigation. */
export function clearPrivateStateSafely(
  stores: readonly (() => KeyStorage)[],
  onError: (index: number) => void,
): void {
  stores.forEach((getStore, index) => {
    try {
      clearPrivateState(getStore());
    } catch {
      onError(index);
    }
  });
}

export function clearBrowserPrivateState(): void {
  clearPrivateStateSafely(
    [() => window.localStorage, () => window.sessionStorage],
    (index) =>
      console.warn(
        "Axiom: private " +
          (index === 0 ? "local" : "session") +
          " storage cleanup unavailable",
      ),
  );
}
