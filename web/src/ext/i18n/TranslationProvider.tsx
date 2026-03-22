"use client";

/**
 * ext-i18n: TranslationProvider für Schicht 2 (DOM-basierte Übersetzung).
 *
 * Übersetzt englische Strings im DOM zur Laufzeit ins Deutsche.
 * Wird in layout.tsx (Core #4) als Wrapper um den App-Content eingebunden.
 *
 * Funktionsweise:
 * 1. Nach dem Mount: Übersetzt den gesamten sichtbaren DOM
 * 2. MutationObserver: Übersetzt dynamisch hinzugefügte Nodes (React Re-Renders)
 * 3. WeakSet verhindert Endlos-Loops (bereits übersetzte Nodes werden übersprungen)
 *
 * Sicherheit: Nur textContent + setAttribute, kein innerHTML (XSS-Prävention)
 */

import { useEffect, useRef } from "react";
import { DE_TRANSLATIONS } from "./translations";

const I18N_ENABLED =
  process.env.NEXT_PUBLIC_EXT_I18N_ENABLED !== "false";

const translatedNodes = new WeakSet<Node>();

function translateTextNode(node: Node): void {
  if (translatedNodes.has(node)) return;

  const raw = node.textContent;
  if (!raw) return;

  const trimmed = raw.trim();
  if (!trimmed) return;

  if (!(trimmed in DE_TRANSLATIONS)) return;
  const translation = DE_TRANSLATIONS[trimmed] ?? "";

  translatedNodes.add(node);
  node.textContent = raw.replace(trimmed, translation);
}

function translateAttributes(element: Element): void {
  const attrs = ["placeholder", "title", "aria-label"] as const;
  for (const attr of attrs) {
    const value = element.getAttribute(attr);
    if (value && value in DE_TRANSLATIONS) {
      element.setAttribute(attr, DE_TRANSLATIONS[value] ?? "");
    }
  }
}

function translateElement(root: Element): void {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    translateTextNode(walker.currentNode);
  }

  translateAttributes(root);
  root
    .querySelectorAll("[placeholder], [title], [aria-label]")
    .forEach((el) => translateAttributes(el));
}

interface TranslationProviderProps {
  children: React.ReactNode;
}

export function TranslationProvider({ children }: TranslationProviderProps) {
  const observerRef = useRef<MutationObserver | null>(null);

  useEffect(() => {
    if (!I18N_ENABLED) return;

    translateElement(document.body);

    observerRef.current = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.TEXT_NODE) {
            translateTextNode(node);
          } else if (node.nodeType === Node.ELEMENT_NODE) {
            translateElement(node as Element);
          }
        });
      }
    });

    observerRef.current.observe(document.body, {
      childList: true,
      subtree: true,
    });

    return () => {
      observerRef.current?.disconnect();
    };
  }, []);

  return <>{children}</>;
}
