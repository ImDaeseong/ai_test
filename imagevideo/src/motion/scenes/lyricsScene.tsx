import {blur, makeScene2D, Rect, Txt} from '@motion-canvas/2d';
import {
  all,
  chain,
  createRef,
  easeInOutCubic,
  easeOutCubic,
  waitFor
} from '@motion-canvas/core';
import {motionPlan} from '../utils/generatedPlan';
import {backgroundFillForSegment, textStyleForProject} from '../styles/typography';
import {
  cameraOffsetFor,
  transitionDurationFor,
  typographyStartFor,
  typographyTargetFor
} from '../utils/animationMapping';

export default makeScene2D(function* (view) {
  const projectStyle = textStyleForProject(motionPlan.project);
  view.fill(projectStyle.stageFill);

  for (const segment of motionPlan.segments) {
    const background = createRef<Rect>();
    const lyric = createRef<Txt>();
    const transitionDuration = transitionDurationFor(segment.motion.transition, segment.duration);
    const introDuration = Math.min(0.55, Math.max(0.25, segment.duration * 0.16));
    const outroDuration = Math.min(0.45, Math.max(0.2, segment.duration * 0.12));
    const holdDuration = Math.max(0.1, segment.duration - introDuration - outroDuration);
    const initial = typographyStartFor(segment.motion.text_animation, motionPlan.project.aspect_ratio);
    const target = typographyTargetFor(segment.motion.text_animation);
    const cameraOffset = cameraOffsetFor(segment.motion.camera, motionPlan.project.aspect_ratio);

    view.add(
      <Rect
        ref={background}
        width={'100%'}
        height={'100%'}
        fill={backgroundFillForSegment(segment)}
        opacity={0}
        scale={1}
      />
    );

    view.add(
      <Txt
        ref={lyric}
        text={segment.lyric}
        fill={projectStyle.fill}
        fontFamily={projectStyle.fontFamily}
        fontSize={projectStyle.fontSize}
        fontWeight={700}
        lineHeight={projectStyle.lineHeight}
        textAlign={'center'}
        width={projectStyle.textWidth}
        shadowBlur={18}
        shadowColor={'rgba(0, 0, 0, 0.42)'}
        stroke={projectStyle.stroke}
        lineWidth={projectStyle.strokeWidth}
        opacity={0}
        scale={initial.scale}
        x={initial.x}
        y={initial.y}
        filters={[blur(initial.blur)]}
      />
    );

    yield* all(
      background().opacity(1, transitionDuration, easeInOutCubic),
      background().scale(1.035, segment.duration, easeInOutCubic),
      background().position(cameraOffset, segment.duration, easeInOutCubic),
      chain(
        all(
          lyric().opacity(1, introDuration, easeOutCubic),
          lyric().scale(target.scale, introDuration, easeOutCubic),
          lyric().position([target.x, target.y], introDuration, easeOutCubic),
          lyric().filters.blur(target.blur, introDuration, easeOutCubic)
        ),
        waitFor(holdDuration),
        all(
          lyric().opacity(0, outroDuration, easeInOutCubic),
          lyric().scale(target.scale * 1.015, outroDuration, easeInOutCubic),
          lyric().filters.blur(8, outroDuration, easeInOutCubic)
        )
      )
    );

    background().remove();
    lyric().remove();
  }
});
