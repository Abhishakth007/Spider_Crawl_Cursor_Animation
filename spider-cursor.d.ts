export interface SpiderCursorOptions {
  /** Folder with the sprite sheets (assets/<size>/<strip>.webp). Default: the assets/ folder next to the script, or the CDN copy. */
  src?: string;
  /** Body length in CSS px, head to abdomen. The legs reach about 1.8x that. Default 34. */
  size?: number;
  /** 1 is a slow crawl, 2 is twice as fast. Default 1. */
  speed?: number;
  /** Hide the arrow while the spider sits on the pointer. Default true. */
  perch?: boolean;
  /** How far short of a moving pointer it stops, in body lengths. Default 0.7. */
  standoff?: number;
  /** "edge": walks in from the nearest edge of the window. "pointer": starts on the pointer. Default "edge". */
  spawn?: "edge" | "pointer";
  /** Now and then wave, tap or groom while standing. Default true. */
  fidget?: boolean;
  /** A soft drop shadow. Default true. */
  shadow?: boolean;
  /** Also for touch input. Default false. */
  touch?: boolean;
  /** Do nothing on windows narrower than this many px. Default 0. */
  minWidth?: number;
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
}

export interface SpiderCursorInstance {
  /** Remove the spider, its listeners and the style that hides the arrow. */
  destroy(): void;
  /** Change options while it runs (size takes effect at once). */
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
