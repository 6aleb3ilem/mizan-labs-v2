// Performance budgets on seeded data (SPEC §27.7): 10 k accounts, 50 k projects, 500 k specimens.
// The list and record scenarios grow with the Phase 1 epics; the thresholds are the contract.
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  scenarios: {
    lists: { executor: "ramping-arrival-rate", startRate: 5, timeUnit: "1s", preAllocatedVUs: 20, maxVUs: 100, stages: [{ target: 40, duration: "2m" }, { target: 40, duration: "3m" }, { target: 0, duration: "1m" }] },
  },
  thresholds: {
    "http_req_duration{kind:read}": ["p(95)<150"],
    "http_req_duration{kind:write}": ["p(95)<400"],
    "http_req_duration{name:project-page}": ["p(95)<1000"],
    http_req_failed: ["rate<0.005"],
  },
};

const BASE = (__ENV.BASE_URL || "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");
let token = __ENV.TOKEN;

export function setup() {
  if (token) return { token };
  const res = http.post(`${BASE}/auth/login`, JSON.stringify({ email: __ENV.EMAIL, password: __ENV.PASSWORD, tenant_code: __ENV.TENANT }), { headers: { "Content-Type": "application/json" } });
  return { token: res.json("access_token") };
}

export default function (data) {
  const auth = { headers: { Authorization: `Bearer ${data.token}` } };
  const lists = ["/users?limit=50", "/audit-events?limit=50", "/notification-deliveries?limit=50", "/services", "/document-templates"];
  const path = lists[Math.floor(Math.random() * lists.length)];
  check(http.get(`${BASE}${path}`, { ...auth, tags: { kind: "read", name: path.split("?")[0] } }), { "200": (r) => r.status === 200 });
  sleep(0.2);
}
