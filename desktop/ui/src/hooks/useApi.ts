import { useCallback, useEffect, useState } from "react";
import axios from "axios";

const DEFAULT_HOST = "http://127.0.0.1:5173";

export function useBackendHost() {
  const [host, setHost] = useState(() => localStorage.getItem("ctxc-host") || DEFAULT_HOST);

  useEffect(() => {
    const update = () => setHost(localStorage.getItem("ctxc-host") || DEFAULT_HOST);
    window.addEventListener("storage", update);
    window.addEventListener("ctxc-host-changed", update as EventListener);
    return () => {
      window.removeEventListener("storage", update);
      window.removeEventListener("ctxc-host-changed", update as EventListener);
    };
  }, []);

  return host;
}

export function useApi<T>(request: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await request();
      setData(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
    } finally {
      setLoading(false);
    }
  }, deps);

  return { data, loading, error, execute };
}

export async function apiClient(path: string, init?: RequestInit) {
  const host = localStorage.getItem("ctxc-host") || DEFAULT_HOST;
  const url = `${host.replace(/\/$/, "")}${path}`;
  const response = await fetch(url, init);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

export async function axiosClient<T>(path: string, method: "get" | "post" | "delete" = "get", body?: unknown) {
  const host = localStorage.getItem("ctxc-host") || DEFAULT_HOST;
  const baseURL = host.replace(/\/$/, "");
  const response = await axios.request<T>({
    baseURL,
    url: path,
    method,
    data: method === "get" || method === "delete" ? undefined : body
  });
  return response.data;
}
