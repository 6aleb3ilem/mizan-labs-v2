// k6 smoke test with the SPEC §1.4 budgets: p95 < 150 ms for reads, < 400 ms for writes.
// Run: k6 run -e BASE_URL=https://api.example/api/v1 -e EMAIL=... -e PASSWORD=... infra/k6/smoke.js
import http from "k6/http";
import { check, group, sleep } from "k6";

export const options = {
  scenarios: {
    smoke: { executor: "constant-vus", vus: Number(__ENV.VUS || 5), duration: __ENV.DURATION || "1m" },
  },
  thresholds: {
    "http_req_duration{kind:read}": ["p(95)<150"],
    "http_req_duration{kind:write}": ["p(95)<400"],
    "http_req_duration{kind:public}": ["p(95)<150"],
    http_req_failed: ["rate<0.01"],
    checks: ["rate>0.99"],
  },
};

const BASE = (__ENV.BASE_URL || "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");

export function setup() {
  const res = http.post(
    `${BASE}/auth/login`,
    JSON.stringify({ email: __ENV.EMAIL || "admin@demo.mizanlabs.dev", password: __ENV.PASSWORD || "Demo-Passw0rd!", tenant_code: __ENV.TENANT || "DEMO" }),
    { headers: { "Content-Type": "application/json", "X-Mizan-App": "back-office" }, tags: { kind: "write" } },
  );
  check(res, { "login 200": (r) => r.status === 200 });
  return { token: res.json("access_token") };
}

export default function (data) {
  const auth = { headers: { Authorization: `Bearer ${data.token}`, "X-Mizan-App": "back-office" } };
  group("public", () => {
    check(http.get(`${BASE}/health`, { tags: { kind: "public" } }), { "health 200": (r) => r.status === 200 });
    check(http.get(`${BASE}/verify/keys`, { tags: { kind: "public" } }), { "jwks 200": (r) => r.status === 200 });
  });
  group("reads", () => {
    for (const path of ["/me", "/me/permissions", "/branches", "/roles", "/numbering-schemes", "/workflows", "/test-definitions", "/notification-rules", "/me/notifications?limit=20"]) {
      const res = http.get(`${BASE}${path}`, { ...auth, tags: { kind: "read", name: path } });
      check(res, { [`${path} 200`]: (r) => r.status === 200 });
    }
  });
  group("writes", () => {
    const res = http.post(`${BASE}/me/notifications:read-all`, null, { ...auth, tags: { kind: "write", name: "read-all" } });
    check(res, { "read-all 200": (r) => r.status === 200 });
  });
  sleep(1);
}
