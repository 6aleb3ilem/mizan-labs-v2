export * from "./client";
export * from "./problem";
export * from "./sse";
export * from "./tokens";
export * from "./react";
export type { components, operations, paths } from "./generated/schema";

import type { components } from "./generated/schema";

/** Convenience aliases of the generated schemas. */
export type Schemas = components["schemas"];
export type Me = Schemas["MeOut"];
export type Permissions = Schemas["PermissionsOut"];
export type Branch = Schemas["BranchOut"];
export type Department = Schemas["DepartmentOut"];
export type Notification = Schemas["NotificationOut"];
