import { Builder } from "@builder.io/react";

const EDITING_QUERY_KEYS = ["builder.mode", "builder.preview", "builder.editing"];

export function isBuilderEditMode() {
  if (typeof window === "undefined") return false;

  try {
    if (Builder?.isEditing) return true;
    if (Builder?.isPreviewing) return true;
  } catch {
    // Ignore SDK access issues and fall back to URL inspection.
  }

  const params = new URLSearchParams(window.location.search);
  return EDITING_QUERY_KEYS.some((key) => params.get(key) === "editing" || params.get(key) === "true") ||
    window.location.search.includes("builder.mode=editing");
}

export function getBuilderEditorLabel() {
  return isBuilderEditMode() ? "Builder Preview Mode" : "Live Mode";
}

