/**
 * ext-i18n: Translation Hook für Schicht 1 (Core-Patches).
 *
 * Verwendung in gepatchten Core-Dateien:
 *   import { t } from "@/ext/i18n";
 *   <button>{t("Sign In")}</button>
 *
 * Feature Flag: NEXT_PUBLIC_EXT_I18N_ENABLED (default: enabled)
 * Fallback: Gibt den Original-String zurück wenn keine Übersetzung existiert.
 */
import { DE_TRANSLATIONS } from "./translations";

const I18N_ENABLED =
  process.env.NEXT_PUBLIC_EXT_I18N_ENABLED !== "false";

export function t(text: string): string {
  if (!I18N_ENABLED) return text;
  return DE_TRANSLATIONS[text] ?? text;
}

export function useTranslation() {
  return { t };
}
