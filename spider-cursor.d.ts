export interface SpiderCursorOptions {
  /** Which spider: "classic" (red and blue) or "widow" (a black widow). Two sets of sprite sheets, rendered from one model and one walk. Default "classic". */
  skin?: "classic" | "widow";
  /** Folder with the sprite sheets (assets/<size>/<strip>.webp). Default: the folder for `skin` next to the script, or the CDN copy. */
  src?: string;
  /** Folder with the lite sheets. Default: inferred from `src` (assets/ -> assets-lite/, assets-widow/ -> assets-widow-lite/). */
  liteSrc?: string;
  /** Body length in CSS px, head to abdomen. The legs reach about 1.85x that. Default 34. */
  size?: number;
  /** 1 is a slow crawl, 2 is twice as fast. Default 1. */
  speed?: number;
  /** Hide the arrow while the spider sits on the pointer. Default true. */
  perch?: boolean;
  /** How far short of a moving pointer it stops, in body lengths. Default 0.7. */
  standoff?: number;
  /** "edge": walks in from the nearest edge of the window. "pointer": starts on the pointer. Default "edge". */
  spawn?: "edge" | "pointer";
  /** "full": every sprite size and gait. "lite": about a fifth of the data and memory. "auto": full, unless the browser asks to save data, is on a slow connection or reports little memory. Default "auto". */
  quality?: "auto" | "full" | "lite";
  /** "auto" honours prefers-reduced-motion (one still frame). "reduced" is that frame, "off" fetches nothing. Default "auto". */
  motion?: "auto" | "full" | "reduced" | "off";
  /** Now and then wave, tap, groom or shift its weight while standing. "auto" is on with full quality. */
  fidget?: boolean | "auto";
  /** The sprites carry their own soft shadow. For packs without one this adds a page drop shadow; "extra" adds it to these too. Default true. */
  shadow?: boolean | "extra";
  /** Also for touch input. Default false. */
  touch?: boolean;
  /** Do nothing on windows narrower than this many px. Default 0. */
  minWidth?: number;
  /** On a desktop, fetch the two sheets it needs as soon as the page is idle. Default true. */
  preload?: boolean;
  /** Once it has appeared, quietly fetch the curved-walk sheets within the memory budget. Default true. */
  prefetch?: boolean;
  /** Decoded-image memory budget in bytes, including images still being decoded. Default 33554432 (32 MiB). */
  cacheBytes?: number;
  /** Decode sheets off the main thread (fetch + createImageBitmap) where a fetch is certain to be allowed: same origin, or jsDelivr / unpkg. Default true. */
  bitmap?: boolean;
  /** After the spider has sat still this many ms, give back the memory of the turning sheets (0 keeps them). Default 20000. */
  idleTrim?: number;
  /** Read manifest.json from `src` instead of the copy built in (only needed if you repacked the sheets with other sizes). Default false. */
  manifest?: boolean;
  /** Default 2147483647. */
  zIndex?: number;
  /** Publish the state on window.__spider every frame. */
  debug?: boolean;
}

export interface SpiderCursorState {
  x: number; y: number; heading: number; v: number; w: number;
  mode: "idle" | "gait" | "stopping";
  strip: string; mirror: boolean; phase: number; perched: boolean;
  tier: number; ready: boolean; idle: string; stripAngle: number; frame: number | null;
  effectiveQuality: "full" | "lite";
  effectiveMotion: "full" | "reduced" | "off";
  cache: { bytes: number; readyBytes: number; pendingBytes: number; pending: number; queued: number; entries: number; configuredLimit: number; limit: number };
  metrics: { rafTicks: number; draws: number };
  error: string | null;
}

export interface SpiderCursorInstance {
  /** Remove the spider, its listeners and the style that hides the arrow. */
  destroy(): void;
  /** Change options while it runs (size takes effect at once; skin, src, quality and motion reload the sheets). */
  set(options: Partial<SpiderCursorOptions>): void;
  setSize(px: number): void;
  show(): void;
  hide(): void;
  /** The spider's pivot (the middle of its feet) and its head, in viewport px. */
  position(): { x: number; y: number; head: { x: number; y: number } };
  state(): SpiderCursorState;
}

export interface SpiderCursorStatic {
  create(options?: SpiderCursorOptions): SpiderCursorInstance;
  version: string;
}

declare const SpiderCursor: SpiderCursorStatic;
export default SpiderCursor;
export const create: SpiderCursorStatic["create"];
export const version: string;
