/**
 * What a clicked value chip puts into the step-4 box.
 * Numeric properties take the first number ("250/300 Bar" -> "250"; any number in the list can match anyway);
 * text properties take the value as printed.
 */
export function fillValue(display: string, dataType: string): string {
  if (dataType !== 'number') return display;
  const m = /\d+(?:\.\d+)?/.exec(display);
  return m ? m[0] : display;
}

/** Message from an NSwag ApiException carrying an RFC 9457 problem body. */
export function problemMessage(e: unknown): string {
  const response = (e as { response?: string } | null)?.response;
  if (response) {
    try {
      const detail = JSON.parse(response).detail;
      if (detail) return String(detail);
    } catch {
      /* not JSON: fall through */
    }
  }
  return e instanceof Error ? e.message : 'Request failed.';
}
