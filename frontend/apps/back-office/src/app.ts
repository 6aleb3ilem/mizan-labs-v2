/** App-wide singletons: the API client with its token store, and the query client. */
import { createMizanApi, createQueryClient, createTokenStore } from "@mizan/api-client";
import { currentLocale } from "@mizan/i18n";

export const API_BASE_URL: string = (import.meta.env["VITE_API_BASE_URL"] as string | undefined) ?? "/api/v1";
export const tokens = createTokenStore("mizan.backoffice.session");
export const api = createMizanApi({
  baseUrl: API_BASE_URL,
  app: "back-office",
  tokens,
  getBranchId: () => globalThis.localStorage?.getItem("mizan.branch"),
  getLocale: () => currentLocale(),
});
export const queryClient = createQueryClient();
