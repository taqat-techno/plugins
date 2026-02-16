/**
 * Remotion Plugin - Multi-Scene Composition Template
 *
 * A data-driven multi-scene composition that reads scene configuration
 * from a JSON timeline. Supports continuous audio, spring transitions,
 * and dynamic scene rendering.
 *
 * Usage:
 *   1. Create a timeline.json in public/content/
 *   2. Register this composition in Root.tsx with calculateMetadata
 *   3. The composition reads timeline data and renders scenes dynamically
 */

import {
  AbsoluteFill,
  Sequence,
  Img,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";
import { Audio } from "@remotion/media";
import { z } from "zod";

// ─── Timeline Schema ───────────────────────────────────────────────────────

const SceneSchema = z.object({
  id: z.string(),
  title: z.string(),
  text: z.string().optional(),
  points: z.array(z.string()).optional(),
  background: z.string().optional(),
  backgroundImage: z.string().optional(),
  startMs: z.number(),
  endMs: z.number(),
  style: z.enum(["title", "content", "image", "split", "outro"]).default("content"),
});

export const TimelineSchema = z.object({
  title: z.string(),
  narrationFile: z.string(),
  totalDurationMs: z.number(),
  scenes: z.array(SceneSchema),
});

type Scene = z.infer<typeof SceneSchema>;
type Timeline = z.infer<typeof TimelineSchema>;

export const multiSceneSchema = z.object({
  timeline: TimelineSchema.nullable(),
});

// ─── Constants ─────────────────────────────────────────────────────────────

const FPS = 30;
const TRANSITION_FRAMES = 10; // Frames for enter/exit transition

// ─── Scene Renderers ───────────────────────────────────────────────────────

const Transition: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const enter = spring({ frame, fps, config: { damping: 200, stiffness: 120 } });
  const exitOpacity = interpolate(
    frame,
    [durationInFrames - TRANSITION_FRAMES, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ opacity: exitOpacity, transform: `scale(${enter})` }}>
      {children}
    </AbsoluteFill>
  );
};

const TitleSlide: React.FC<{ scene: Scene }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const titleY = interpolate(frame, [0, 25], [40, 0], { extrapolateRight: "clamp" });
  const titleOp = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: "clamp" });
  const subOp = interpolate(frame, [15, 35], [0, 1], { extrapolateRight: "clamp" });

  return (
    <Transition>
      <AbsoluteFill
        style={{
          backgroundColor: scene.background || "#0f172a",
          justifyContent: "center",
          alignItems: "center",
          padding: 80,
        }}
      >
        <h1 style={{
          color: "#fff", fontSize: 72, fontWeight: 700, textAlign: "center",
          opacity: titleOp, transform: `translateY(${titleY}px)`,
        }}>
          {scene.title}
        </h1>
        {scene.text && (
          <p style={{ color: "#94a3b8", fontSize: 28, textAlign: "center", opacity: subOp, marginTop: 24 }}>
            {scene.text}
          </p>
        )}
      </AbsoluteFill>
    </Transition>
  );
};

const ContentSlide: React.FC<{ scene: Scene }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const titleOp = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  return (
    <Transition>
      <AbsoluteFill
        style={{
          backgroundColor: scene.background || "#1e293b",
          padding: 80,
          justifyContent: "center",
        }}
      >
        <h2 style={{ color: "#fff", fontSize: 48, fontWeight: 600, opacity: titleOp, marginBottom: 40 }}>
          {scene.title}
        </h2>

        {scene.points?.map((point, i) => {
          const delay = 15 + i * 12;
          const op = interpolate(frame, [delay, delay + 12], [0, 1], {
            extrapolateLeft: "clamp", extrapolateRight: "clamp",
          });
          const x = interpolate(frame, [delay, delay + 12], [30, 0], {
            extrapolateLeft: "clamp", extrapolateRight: "clamp",
          });

          return (
            <div key={i} style={{
              opacity: op, transform: `translateX(${x}px)`,
              marginBottom: 18, display: "flex", alignItems: "center", gap: 14,
            }}>
              <div style={{
                width: 8, height: 8, borderRadius: "50%",
                backgroundColor: "#3b82f6", flexShrink: 0,
              }} />
              <span style={{ color: "#e2e8f0", fontSize: 26 }}>{point}</span>
            </div>
          );
        })}

        {scene.text && !scene.points && (
          <p style={{
            color: "#cbd5e1", fontSize: 24, lineHeight: 1.6,
            opacity: interpolate(frame, [10, 25], [0, 1], { extrapolateRight: "clamp" }),
          }}>
            {scene.text}
          </p>
        )}
      </AbsoluteFill>
    </Transition>
  );
};

const ImageSlide: React.FC<{ scene: Scene }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const zoom = interpolate(frame, [0, durationInFrames], [1, 1.08], {
    extrapolateRight: "clamp",
  });
  const textOp = interpolate(frame, [15, 30], [0, 1], { extrapolateRight: "clamp" });

  return (
    <Transition>
      <AbsoluteFill>
        {scene.backgroundImage && (
          <Img
            src={staticFile(scene.backgroundImage)}
            style={{
              width: "100%", height: "100%", objectFit: "cover",
              transform: `scale(${zoom})`,
            }}
          />
        )}
        <AbsoluteFill style={{
          background: "linear-gradient(transparent 50%, rgba(0,0,0,0.8) 100%)",
          justifyContent: "flex-end", padding: 60,
        }}>
          <h2 style={{ color: "#fff", fontSize: 48, fontWeight: 600, opacity: textOp }}>
            {scene.title}
          </h2>
          {scene.text && (
            <p style={{ color: "#e2e8f0", fontSize: 24, opacity: textOp, marginTop: 12 }}>
              {scene.text}
            </p>
          )}
        </AbsoluteFill>
      </AbsoluteFill>
    </Transition>
  );
};

// ─── Scene Renderer Mapping ────────────────────────────────────────────────

const SCENE_RENDERERS: Record<string, React.FC<{ scene: Scene }>> = {
  title: TitleSlide,
  content: ContentSlide,
  image: ImageSlide,
  split: ContentSlide,
  outro: TitleSlide,
};

const renderScene = (scene: Scene) => {
  const Renderer = SCENE_RENDERERS[scene.style] || ContentSlide;
  return <Renderer scene={scene} />;
};

// ─── Main Composition ──────────────────────────────────────────────────────

export const MultiSceneVideo: React.FC<z.infer<typeof multiSceneSchema>> = ({
  timeline,
}) => {
  if (!timeline) {
    throw new Error("Timeline data is required. Provide it via calculateMetadata.");
  }

  return (
    <AbsoluteFill style={{ backgroundColor: "#0f172a" }}>
      {/* CONTINUOUS AUDIO - Single track at root, never cuts */}
      <Audio src={staticFile(timeline.narrationFile)} />

      {/* VISUAL SCENES - Purely visual, don't affect audio */}
      {timeline.scenes.map((scene, index) => {
        const startFrame = Math.ceil(scene.startMs * FPS / 1000);
        const durationFrames = Math.ceil((scene.endMs - scene.startMs) * FPS / 1000);

        return (
          <Sequence
            key={scene.id || index}
            from={startFrame}
            durationInFrames={durationFrames}
          >
            {renderScene(scene)}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
