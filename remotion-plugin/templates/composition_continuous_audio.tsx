/**
 * Remotion Plugin - Continuous Audio Composition Template
 *
 * This is the CORRECT pattern for videos with voice narration.
 * Audio is placed at the ROOT level so it NEVER cuts between slides.
 *
 * How it works:
 * 1. ONE <Audio> component at the root spans the entire video
 * 2. <Sequence> components control ONLY visual elements
 * 3. Voice plays smoothly through all slide transitions
 *
 * Usage:
 *   Copy this file to src/compositions/MyVideo.tsx
 *   Update SCENES with your scene durations (from concat_audio.py output)
 *   Create scene components in src/compositions/scenes/
 */

import {
  AbsoluteFill,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";
import { Audio } from "@remotion/media";

// ─── Scene Configuration ───────────────────────────────────────────────────
// These values come from concat_audio.py output (segment timestamps)
// Run: python concat_audio.py --files scene01.mp3 scene02.mp3 ... --output narration.mp3
// Then use the "segments" array from the JSON output

const FPS = 30;

const SCENES = [
  { name: "intro", startFrame: 0, durationFrames: 150, title: "Welcome" },
  { name: "content1", startFrame: 156, durationFrames: 300, title: "Key Point 1" },
  { name: "content2", startFrame: 462, durationFrames: 300, title: "Key Point 2" },
  { name: "outro", startFrame: 768, durationFrames: 120, title: "Thank You" },
];

// ─── Scene Components ──────────────────────────────────────────────────────

const SceneTransition: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Spring entrance animation
  const enterScale = spring({
    frame,
    fps,
    config: { damping: 200, stiffness: 100 },
  });

  // Fade out in last 10 frames
  const exitOpacity = interpolate(
    frame,
    [durationInFrames - 10, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill
      style={{
        opacity: exitOpacity,
        transform: `scale(${enterScale})`,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

const TitleScene: React.FC<{ title: string; subtitle?: string }> = ({
  title,
  subtitle,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });
  const titleY = interpolate(frame, [0, 20], [30, 0], {
    extrapolateRight: "clamp",
  });
  const subtitleOpacity = interpolate(frame, [15, 35], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <SceneTransition>
      <AbsoluteFill
        style={{
          backgroundColor: "#0f172a",
          justifyContent: "center",
          alignItems: "center",
          padding: 80,
        }}
      >
        <h1
          style={{
            color: "#ffffff",
            fontSize: 72,
            fontWeight: 700,
            textAlign: "center",
            opacity: titleOpacity,
            transform: `translateY(${titleY}px)`,
            margin: 0,
          }}
        >
          {title}
        </h1>
        {subtitle && (
          <p
            style={{
              color: "#94a3b8",
              fontSize: 32,
              textAlign: "center",
              opacity: subtitleOpacity,
              marginTop: 20,
            }}
          >
            {subtitle}
          </p>
        )}
      </AbsoluteFill>
    </SceneTransition>
  );
};

const ContentScene: React.FC<{
  title: string;
  points: string[];
  backgroundColor?: string;
}> = ({ title, points, backgroundColor = "#1e293b" }) => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <SceneTransition>
      <AbsoluteFill
        style={{
          backgroundColor,
          padding: 80,
          justifyContent: "center",
        }}
      >
        <h2
          style={{
            color: "#ffffff",
            fontSize: 48,
            fontWeight: 600,
            marginBottom: 40,
            opacity: titleOpacity,
          }}
        >
          {title}
        </h2>

        {points.map((point, index) => {
          const delay = 20 + index * 15;
          const opacity = interpolate(frame, [delay, delay + 15], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const translateX = interpolate(
            frame,
            [delay, delay + 15],
            [40, 0],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }
          );

          return (
            <div
              key={index}
              style={{
                opacity,
                transform: `translateX(${translateX}px)`,
                marginBottom: 20,
                display: "flex",
                alignItems: "center",
                gap: 16,
              }}
            >
              <div
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  backgroundColor: "#3b82f6",
                  flexShrink: 0,
                }}
              />
              <span style={{ color: "#e2e8f0", fontSize: 28 }}>{point}</span>
            </div>
          );
        })}
      </AbsoluteFill>
    </SceneTransition>
  );
};

// ─── Main Composition ──────────────────────────────────────────────────────

export const ContinuousAudioVideo: React.FC = () => {
  return (
    <AbsoluteFill>
      {/*
       * CRITICAL: Single audio at the root level.
       * This audio spans the ENTIRE video duration.
       * It NEVER cuts, even when visual scenes transition.
       *
       * The narration.mp3 file is created by concat_audio.py
       * from individual per-scene MP3 files.
       */}
      <Audio src={staticFile("audio/narration.mp3")} />

      {/*
       * Visual scenes below. These Sequences ONLY control
       * what's visible on screen. They do NOT affect audio.
       */}
      <Sequence
        from={SCENES[0].startFrame}
        durationInFrames={SCENES[0].durationFrames}
      >
        <TitleScene
          title="Presentation Title"
          subtitle="Your subtitle here"
        />
      </Sequence>

      <Sequence
        from={SCENES[1].startFrame}
        durationInFrames={SCENES[1].durationFrames}
      >
        <ContentScene
          title="Key Point 1"
          points={[
            "First important detail",
            "Second important detail",
            "Third important detail",
          ]}
        />
      </Sequence>

      <Sequence
        from={SCENES[2].startFrame}
        durationInFrames={SCENES[2].durationFrames}
      >
        <ContentScene
          title="Key Point 2"
          points={[
            "Another insight",
            "Supporting evidence",
            "Final thought on this topic",
          ]}
          backgroundColor="#0c4a6e"
        />
      </Sequence>

      <Sequence
        from={SCENES[3].startFrame}
        durationInFrames={SCENES[3].durationFrames}
      >
        <TitleScene title="Thank You" subtitle="www.example.com" />
      </Sequence>
    </AbsoluteFill>
  );
};
