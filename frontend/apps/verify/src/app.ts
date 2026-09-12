/** The verification site is public: no session, plain fetch of the public verification endpoints. */
import { createMizanApi, createMemoryStorage, createTokenStore } from "@mizan/api-client";

export const API_BASE_URL: string = (import.meta.env["VITE_API_BASE_URL"] as string | undefined) ?? "/api/v1";
export const api = createMizanApi({ baseUrl: API_BASE_URL, app: "verify", tokens: createTokenStore("mizan.verify", createMemoryStorage()) });
