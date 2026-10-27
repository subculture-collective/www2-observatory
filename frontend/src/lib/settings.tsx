import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export const WINDOWS = [
  { hours: 1, label: "1h" },
  { hours: 6, label: "6h" },
  { hours: 24, label: "24h" },
  { hours: 72, label: "3d" },
  { hours: 168, label: "7d" },
  { hours: 336, label: "14d" },
  { hours: 720, label: "30d" },
  { hours: 2160, label: "90d" },
];

interface Settings {
  hours: number;
  setHours: (h: number) => void;
  refreshSeconds: number;
  setRefreshSeconds: (s: number) => void;
  crt: boolean;
  setCrt: (v: boolean) => void;
  motion: boolean;
  /** Incremented every refresh tick; data hooks depend on it. */
  tick: number;
  refreshNow: () => void;
  lastRefresh: number;
}

const Ctx = createContext<Settings | null>(null);

function stored<T>(key: string, fallback: T, parse: (v: string) => T): T {
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return fallback;
    return parse(raw);
  } catch {
    return fallback;
  }
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [hours, setHoursState] = useState(() =>
    stored("obs_display_version", "", String) === "2"
      ? stored("obs_hours", 720, (v) =>
          WINDOWS.some((w) => w.hours === Number(v)) ? Number(v) : 720,
        )
      : 720,
  );
  const [refreshSeconds, setRefreshState] = useState(() =>
    stored("obs_display_version", "", String) === "2"
      ? stored("obs_refresh", 30, (v) =>
          [0, 15, 30, 60, 300].includes(Number(v)) ? Number(v) : 30,
        )
      : 30,
  );
  const [crt, setCrtState] = useState(() =>
    stored("obs_crt", true, (v) => v === "on"),
  );
  const [motion, setMotion] = useState(
    () => !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const [tick, setTick] = useState(0);
  const [lastRefresh, setLastRefresh] = useState(Date.now());

  const setHours = useCallback((h: number) => {
    localStorage.setItem("obs_hours", String(h));
    setHoursState(h);
  }, []);
  const setRefreshSeconds = useCallback((s: number) => {
    localStorage.setItem("obs_refresh", String(s));
    setRefreshState(s);
  }, []);
  const setCrt = useCallback((v: boolean) => {
    localStorage.setItem("obs_crt", v ? "on" : "off");
    setCrtState(v);
  }, []);
  useEffect(() => {
    localStorage.setItem("obs_display_version", "2");
    localStorage.setItem("obs_hours", String(hours));
    localStorage.setItem("obs_refresh", String(refreshSeconds));
    localStorage.removeItem("obs_tilt");
    localStorage.removeItem("obs_motion");
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setMotion(!media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []); // Initial migration; subsequent choices are saved by their setters.
  const refreshNow = useCallback(() => {
    setTick((t) => t + 1);
    setLastRefresh(Date.now());
  }, []);

  useEffect(() => {
    if (refreshSeconds <= 0) return;
    const id = window.setInterval(refreshNow, refreshSeconds * 1000);
    return () => window.clearInterval(id);
  }, [refreshSeconds, refreshNow]);

  useEffect(() => {
    document.body.classList.toggle("crt", crt);
    document.body.classList.toggle("no-motion", !motion);
    document.body.classList.remove("tilt");
  }, [crt, motion]);

  const value = useMemo<Settings>(
    () => ({
      hours,
      setHours,
      refreshSeconds,
      setRefreshSeconds,
      crt,
      setCrt,
      motion,
      tick,
      refreshNow,
      lastRefresh,
    }),
    [
      hours,
      setHours,
      refreshSeconds,
      setRefreshSeconds,
      crt,
      setCrt,
      motion,
      tick,
      refreshNow,
      lastRefresh,
    ],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSettings(): Settings {
  const v = useContext(Ctx);
  if (!v) throw new Error("SettingsProvider missing");
  return v;
}

/**
 * Fetch data whenever the window or the refresh tick changes. Keeps the last
 * good value visible while a refresh is in flight or fails.
 */
export function useData<T>(
  loader: (hours: number) => Promise<T>,
  deps: unknown[] = [],
): { data: T | null; error: string; loading: boolean } {
  const { hours, tick } = useSettings();
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let alive = true;
    setLoading(true);
    loader(hours)
      .then((v) => {
        if (!alive) return;
        setData(v);
        setError("");
      })
      .catch(
        (e: unknown) =>
          alive && setError(e instanceof Error ? e.message : String(e)),
      )
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hours, tick, ...deps]);
  return { data, error, loading };
}
