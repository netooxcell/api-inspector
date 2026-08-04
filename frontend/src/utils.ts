export function statusBadgeClass(status: number | null): string {
  if (status === null) return "badge-timeout";
  if (status >= 200 && status < 300) return "badge-2xx";
  if (status >= 300 && status < 400) return "badge-3xx";
  if (status >= 400 && status < 500) return "badge-4xx";
  if (status >= 500 && status < 600) return "badge-5xx";
  return "badge-neutral";
}

export function durationBadgeClass(ms: number | null): string {
  if (ms === null) return "duration-med";
  if (ms < 200) return "duration-fast";
  if (ms <= 1000) return "duration-med";
  return "duration-slow";
}

export function formatTime(ts: string): string {
  const d = new Date(ts.includes("Z") || ts.includes("+") ? ts : ts + "Z");
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function hostFromUrl(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}

export function isJsonLike(value: unknown): boolean {
  return typeof value === "object" && value !== null;
}

export function tryFormatBody(body: unknown): string {
  if (body === null || body === undefined) return "";
  if (typeof body === "string") {
    try {
      return JSON.stringify(JSON.parse(body), null, 2);
    } catch {
      return body;
    }
  }
  try {
    return JSON.stringify(body, null, 2);
  } catch {
    return String(body);
  }
}
