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
