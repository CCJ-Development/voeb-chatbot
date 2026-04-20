"use client";

import { useEffect, useMemo } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { useSettingsContext } from "@/providers/SettingsProvider";

export default function DynamicMetadata() {
  const { enterpriseSettings } = useSettingsContext();
  // pathname + searchParams deps re-sync document.title after soft-navigations.
  // Next.js App Router re-injects the static metadata.title into <head> on both
  // pathname changes AND query-only transitions (e.g. chat switch via ?chatId=).
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    const title = enterpriseSettings?.application_name || "Onyx";
    if (document.title !== title) {
      document.title = title;
    }
  }, [enterpriseSettings, pathname, searchParams]);

  // Cache-buster so the favicon re-fetches after an admin uploads a new logo.
  const cacheBuster = useMemo(
    () => Date.now(),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [enterpriseSettings]
  );

  const favicon = enterpriseSettings?.use_custom_logo
    ? `/api/enterprise-settings/logo?v=${cacheBuster}`
    : "/onyx.ico";

  return <link rel="icon" href={favicon} />;
}
