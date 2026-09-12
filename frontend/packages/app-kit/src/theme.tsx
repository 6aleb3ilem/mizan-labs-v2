import { applyTheme, type ThemeName } from "@mizan/tokens";
import { paletteVariables } from "@mizan/ui";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type ThemeChoice = ThemeName | "system";
type ThemeContextValue = { choice: ThemeChoice; theme: ThemeName; setChoice: (choice: ThemeChoice) => void; brand: string | undefined; setBrand: (brand: string | undefined) => void };

const ThemeContext = createContext<ThemeContextValue | null>(null);
const STORAGE_KEY = "mizan.theme";

function systemTheme(): ThemeName {
  return globalThis.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function readChoice(): ThemeChoice {
  try {
    const value = globalThis.localStorage?.getItem(STORAGE_KEY);
    return value === "light" || value === "dark" || value === "system" ? value : "system";
  } catch {
    return "system";
  }
}

/** Light/dark/system with the tenant primary colour applied to the document root (SPEC §21.2). */
export function ThemeProvider({ children, initialBrand }: { children: ReactNode; initialBrand?: string }) {
  const [choice, setChoiceState] = useState<ThemeChoice>(readChoice);
  const [system, setSystem] = useState<ThemeName>(systemTheme);
  const [brand, setBrand] = useState<string | undefined>(initialBrand);
  const theme = choice === "system" ? system : choice;

  useEffect(() => {
    const media = globalThis.matchMedia?.("(prefers-color-scheme: dark)");
    if (!media) return;
    const listener = () => setSystem(systemTheme());
    media.addEventListener("change", listener);
    return () => media.removeEventListener("change", listener);
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    applyTheme(root, theme, brand);
    for (const [name, value] of Object.entries(paletteVariables(theme))) root.style.setProperty(name, value);
  }, [theme, brand]);

  const setChoice = useCallback((next: ThemeChoice) => {
    setChoiceState(next);
    try {
      globalThis.localStorage?.setItem(STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
  }, []);

  const value = useMemo(() => ({ choice, theme, setChoice, brand, setBrand }), [choice, theme, setChoice, brand]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const value = useContext(ThemeContext);
  if (!value) throw new Error("useTheme must be used inside <ThemeProvider>");
  return value;
}
