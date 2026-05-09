import type {MotionPlanProject, MotionPlanSegment} from '../utils/generatedPlan';

const PALETTE_FILLS: Record<string, string> = {
  navy: '#071423',
  gold: '#d7a64a',
  cyan: '#33d3ee',
  violet: '#6f5cff',
  coral: '#ff6d5f',
  gray: '#2a3038',
  teal: '#0f6f72',
  black: '#07090d'
};

export function textStyleForProject(project: MotionPlanProject) {
  const vertical = project.aspect_ratio === '9:16';
  const square = project.aspect_ratio === '1:1';

  return {
    fill: '#ffffff',
    stroke: 'rgba(12, 16, 24, 0.72)',
    strokeWidth: vertical ? 7 : 5,
    fontFamily: fontFamilyFor(project.font_style),
    fontSize: vertical ? 78 : square ? 64 : 68,
    lineHeight: 1.12,
    textWidth: vertical ? 860 : square ? 880 : 1320,
    stageFill: '#080b12'
  };
}

export function backgroundFillForSegment(segment: MotionPlanSegment) {
  const palette = segment.style.color_palette.toLowerCase();
  const colorA = pickColor(palette, '#101827');
  const colorB = palette.includes('gold') ? '#2d2514' : palette.includes('coral') ? '#2b171d' : '#142032';

  return {
    type: 'linear',
    from: [-960, -540],
    to: [960, 540],
    stops: [
      {offset: 0, color: colorA},
      {offset: 0.52, color: '#0c111d'},
      {offset: 1, color: colorB}
    ]
  };
}

function pickColor(palette: string, fallback: string) {
  for (const [name, value] of Object.entries(PALETTE_FILLS)) {
    if (palette.includes(name)) {
      return value;
    }
  }

  return fallback;
}

function fontFamilyFor(fontStyle: string) {
  const normalized = fontStyle.toLowerCase();
  if (normalized.includes('condensed')) {
    return 'Arial Narrow, Arial, sans-serif';
  }
  if (normalized.includes('humanist')) {
    return 'Trebuchet MS, Arial, sans-serif';
  }
  return 'Arial, Helvetica, sans-serif';
}
