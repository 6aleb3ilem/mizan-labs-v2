/** RFC 9457 problem details as produced by the API (SPEC §27.3) and the client-side error type. */

export type ProblemDetail = { loc?: (string | number)[]; msg?: string; type?: string };

export type Problem = {
  type: string;
  title: string;
  status: number;
  detail: string;
  code: string;
  message_key: string;
  params: Record<string, unknown>;
  details: ProblemDetail[];
  request_id?: string;
};

export class ApiError extends Error {
  readonly problem: Problem;
  readonly status: number;

  constructor(problem: Problem) {
    super(problem.detail || problem.message_key || `HTTP ${problem.status}`);
    this.name = "ApiError";
    this.problem = problem;
    this.status = problem.status;
  }

  get code(): string {
    return this.problem.code;
  }

  get messageKey(): string {
    return this.problem.message_key;
  }

  /** Field errors keyed by the first path element (`loc[0]`). */
  fieldErrors(): Record<string, string> {
    const errors: Record<string, string> = {};
    for (const d of this.problem.details ?? []) {
      const key = String(d.loc?.[d.loc.length - 1] ?? d.loc?.[0] ?? "");
      if (key && !(key in errors)) errors[key] = d.msg ?? "";
    }
    return errors;
  }

  static is(error: unknown): error is ApiError {
    return error instanceof ApiError;
  }
}

export class NetworkError extends Error {
  constructor(cause: unknown) {
    super("network error");
    this.name = "NetworkError";
    this.cause = cause;
  }
}

export function problemFrom(status: number, body: unknown): Problem {
  const raw = (typeof body === "object" && body !== null ? body : {}) as Partial<Problem>;
  return {
    type: raw.type ?? `urn:mizan:error:http_${status}`,
    title: raw.title ?? `HTTP ${status}`,
    status: raw.status ?? status,
    detail: raw.detail ?? "",
    code: raw.code ?? `http_${status}`,
    message_key: raw.message_key ?? `common.http_${status}`,
    params: raw.params ?? {},
    details: raw.details ?? [],
    request_id: raw.request_id,
  };
}
