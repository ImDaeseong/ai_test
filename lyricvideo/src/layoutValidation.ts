export interface LayoutRect {
  readonly role: string;
  readonly left: number;
  readonly top: number;
  readonly right: number;
  readonly bottom: number;
}

/** Returns deterministic clipping and overlap diagnostics for visible lyric boxes. */
export const validateLayoutRects = (
  canvas: Omit<LayoutRect, 'role'>,
  rects: readonly LayoutRect[],
  padding = 0,
): string[] => {
  const visible = rects.filter((rect) => rect.right > rect.left && rect.bottom > rect.top);
  const diagnostics: string[] = [];

  for (const rect of visible) {
    if (
      rect.left < canvas.left + padding ||
      rect.top < canvas.top + padding ||
      rect.right > canvas.right - padding ||
      rect.bottom > canvas.bottom - padding
    ) {
      diagnostics.push(`${rect.role} is clipped outside the render canvas`);
    }
  }

  for (let first = 0; first < visible.length; first += 1) {
    for (let second = first + 1; second < visible.length; second += 1) {
      const a = visible[first]!;
      const b = visible[second]!;
      const overlaps =
        a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
      if (overlaps) diagnostics.push(`${a.role} overlaps ${b.role}`);
    }
  }

  return diagnostics;
};
