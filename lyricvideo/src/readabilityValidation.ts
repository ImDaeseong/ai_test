import type {LyricLine} from './parsers';

export interface RgbaColor {
  readonly red: number;
  readonly green: number;
  readonly blue: number;
  readonly alpha: number;
}

/** Composites a foreground color over an opaque background color. */
export const compositeColor = (foreground: RgbaColor, background: RgbaColor): RgbaColor => ({
  red: foreground.red * foreground.alpha + background.red * (1 - foreground.alpha),
  green: foreground.green * foreground.alpha + background.green * (1 - foreground.alpha),
  blue: foreground.blue * foreground.alpha + background.blue * (1 - foreground.alpha),
  alpha: 1,
});

const linearChannel = (channel: number): number => {
  const normalized = channel / 255;
  return normalized <= 0.04045
    ? normalized / 12.92
    : ((normalized + 0.055) / 1.055) ** 2.4;
};

/** Calculates the WCAG relative-luminance contrast ratio between opaque colors. */
export const contrastRatio = (first: RgbaColor, second: RgbaColor): number => {
  const luminance = (color: RgbaColor) =>
    0.2126 * linearChannel(color.red) +
    0.7152 * linearChannel(color.green) +
    0.0722 * linearChannel(color.blue);
  const brighter = Math.max(luminance(first), luminance(second));
  const darker = Math.min(luminance(first), luminance(second));
  return (brighter + 0.05) / (darker + 0.05);
};

/** Reports lyric lines that exceed the project's space or reading-speed limits. */
export const validateLyricReadability = (lyrics: readonly LyricLine[]): string[] => {
  const diagnostics: string[] = [];

  lyrics.forEach((line, index) => {
    const graphemeCount = [...new Intl.Segmenter(undefined, {granularity: 'grapheme'}).segment(line.text)]
      .length;
    const duration = Math.max(line.end - line.start, 0.001);
    if (graphemeCount > 80) diagnostics.push(`line ${index + 1} exceeds 80 graphemes`);
    else if (graphemeCount / duration > 20) {
      diagnostics.push(`line ${index + 1} exceeds 20 graphemes per second`);
    }
  });

  return diagnostics;
};
