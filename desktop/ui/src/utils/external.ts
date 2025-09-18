export async function openExternalLink(url: string): Promise<void> {
  if (typeof window === "undefined") {
    return;
  }

  const normalized = url.trim();
  if (!normalized) {
    return;
  }

  const tauriShell = (window as unknown as {
    __TAURI__?: {
      shell?: {
        open?: (target: string) => Promise<void> | void;
      };
    };
  }).__TAURI__?.shell;

  if (tauriShell?.open) {
    try {
      await tauriShell.open(normalized);
      return;
    } catch (error) {
      console.warn("Failed to open link via Tauri shell", error);
    }
  }

  window.open(normalized, "_blank", "noopener");
}
