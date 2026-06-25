import { useState, useEffect, useRef, useCallback } from "react";
import { getVideoResult, resolveApiUrl, ApiError } from "../api";
import type { VideoResult, VideoTaskStatus } from "../types/video";

// ── Hook state ─────────────────────────────────────

export interface UseVideoResultState {
  /** Whether a request is currently in flight. */
  loading: boolean;
  /** The normalized result, or null if not yet loaded / errored. */
  data: VideoResult | null;
  /** The error, or null if no error occurred. */
  error: string | null;
  /** The raw ``ApiError`` (for status code inspection), or null. */
  apiError: ApiError | null;
}

export interface UseVideoResultReturn extends UseVideoResultState {
  /** Re-fetch the result. */
  reload: () => void;
}

// ── Hook ───────────────────────────────────────────

/**
 * Fetch and normalize the video result for a given videoId.
 *
 * - Pass ``null`` or empty ``videoId`` to skip fetching.
 * - Pass ``{enabled: false}`` to temporarily suspend fetching.
 * - Aborts the previous request when ``videoId`` changes.
 * - Ignores ``AbortError`` (does not surface it as ``error``).
 * - Returns a ``reload`` function for manual retrigger.
 */
export function useVideoResult(
  videoId: string | null,
  options?: { enabled?: boolean },
): UseVideoResultReturn {
  const enabled = options?.enabled ?? true;
  const [state, setState] = useState<UseVideoResultState>({
    loading: false,
    data: null,
    error: null,
    apiError: null,
  });

  // Use a counter to track the latest request (avoids stale updates)
  const counterRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  const fetchResult = useCallback(() => {
    // Clean up previous request
    if (abortRef.current) {
      abortRef.current.abort();
    }

    if (!videoId || !enabled) {
      setState({ loading: false, data: null, error: null, apiError: null });
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;
    const currentCounter = ++counterRef.current;

    setState((prev) => ({ ...prev, loading: true, error: null, apiError: null }));

    getVideoResult(videoId, controller.signal)
      .then((result) => {
        // Only apply if this is still the latest request
        if (currentCounter !== counterRef.current) return;
        setState({
          loading: false,
          data: result,
          error: null,
          apiError: null,
        });
      })
      .catch((err: unknown) => {
        if (currentCounter !== counterRef.current) return;
        // Ignore AbortError (expected when a new request supersedes this one)
        if (err instanceof DOMException && err.name === "AbortError") {
          setState((prev) => ({ ...prev, loading: false }));
          return;
        }
        if (err instanceof ApiError) {
          setState({
            loading: false,
            data: null,
            error: err.detail || err.message,
            apiError: err,
          });
        } else {
          const msg = err instanceof Error ? err.message : String(err);
          setState({
            loading: false,
            data: null,
            error: msg,
            apiError: null,
          });
        }
      });
  }, [videoId, enabled]);

  // Trigger fetch when videoId or enabled changes
  useEffect(() => {
    fetchResult();
    return () => {
      if (abortRef.current) {
        abortRef.current.abort();
      }
    };
  }, [fetchResult]);

  const reload = useCallback(() => {
    fetchResult();
  }, [fetchResult]);

  return { ...state, reload };
}
