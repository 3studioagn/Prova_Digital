"use client";

import { useCallback, useEffect, useRef } from "react";

/**
 * Fires `onTimeout` after `timeoutMs` of user inactivity.
 * Resets on mouse, keyboard, touch and scroll events.
 *
 * RNF-003: sessoes inativas por mais de 30 min devem ser encerradas.
 */
export function useInactivityTimeout(
  timeoutMs: number,
  onTimeout: () => void
) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const callbackRef = useRef(onTimeout);
  callbackRef.current = onTimeout;

  const reset = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => callbackRef.current(), timeoutMs);
  }, [timeoutMs]);

  useEffect(() => {
    const events = ["mousedown", "keydown", "touchstart", "scroll"] as const;
    events.forEach((e) => window.addEventListener(e, reset));
    reset();

    return () => {
      events.forEach((e) => window.removeEventListener(e, reset));
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [reset]);
}
