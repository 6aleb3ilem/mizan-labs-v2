// Shared flat ESLint configuration: TypeScript strict rules, React hooks, browser globals.
import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

/** @param {{ ignores?: string[] }} [options] */
export function mizanEslint(options = {}) {
  return tseslint.config(
    { ignores: ["dist/**", "storybook-static/**", "node_modules/**", "src/generated/**", ...(options.ignores ?? [])] },
    js.configs.recommended,
    ...tseslint.configs.recommended,
    {
      files: ["**/*.{ts,tsx}"],
      languageOptions: { globals: { ...globals.browser, ...globals.node } },
      plugins: { "react-hooks": reactHooks },
      rules: {
        ...reactHooks.configs.recommended.rules,
        "@typescript-eslint/consistent-type-imports": ["error", { prefer: "type-imports", fixStyle: "inline-type-imports" }],
        "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
        "@typescript-eslint/no-explicit-any": "error",
        "no-console": ["warn", { allow: ["warn", "error"] }],
      },
    },
    {
      files: ["**/*.{test,spec,stories}.{ts,tsx}", "**/vitest.config.ts", "**/vite.config.ts", "**/.storybook/**"],
      rules: { "no-console": "off" },
    },
  );
}
