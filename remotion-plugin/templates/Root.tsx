/**
 * Remotion Plugin - Root Composition Template
 *
 * This file registers all compositions in your Remotion project.
 * Copy to src/Root.tsx and customize with your compositions.
 *
 * Two patterns are shown:
 * 1. Static duration - when you know the exact length
 * 2. Dynamic duration - when duration depends on audio/timeline data
 */

import { Composition, staticFile } from "remotion";
import "./index.css"; // TailwindCSS import

// Import your compositions
import { ContinuousAudioVideo } from "./compositions/ContinuousAudioVideo";
import {
  MultiSceneVideo,
  multiSceneSchema,
  TimelineSchema,
} from "./compositions/MultiSceneVideo";

const FPS = 30;
const PADDING_FRAMES = 30; // 1 second padding after audio ends

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/*
       * Pattern 1: Static Duration
       * Use when you know the exact duration (e.g., from concat_audio.py output)
       *
       * After running concat_audio.py, use "total_frames_with_padding" as durationInFrames
       */}
      <Composition
        id="ContinuousAudioVideo"
        component={ContinuousAudioVideo}
        durationInFrames={900} // Update with concat_audio.py output
        fps={FPS}
        width={1920}
        height={1080}
      />

      {/*
       * Pattern 2: Dynamic Duration (Recommended)
       * Duration is calculated from the timeline.json file
       * This auto-adjusts when audio changes
       */}
      <Composition
        id="MultiSceneVideo"
        component={MultiSceneVideo}
        fps={FPS}
        width={1920}
        height={1080}
        schema={multiSceneSchema}
        calculateMetadata={async () => {
          try {
            const res = await fetch(
              staticFile("content/timeline.json")
            );
            const data = await res.json();
            const timeline = TimelineSchema.parse(data);

            // Calculate duration from timeline
            const lastScene = timeline.scenes[timeline.scenes.length - 1];
            const totalMs = lastScene?.endMs ?? timeline.totalDurationMs;
            const durationInFrames =
              Math.ceil((totalMs / 1000) * FPS) + PADDING_FRAMES;

            return {
              durationInFrames,
              props: { timeline },
            };
          } catch (error) {
            // Fallback: use default props if timeline not found
            return {
              durationInFrames: 300,
              props: { timeline: null },
            };
          }
        }}
      />

      {/*
       * Pattern 3: Portrait Video (for social media)
       * Same composition, different dimensions
       */}
      <Composition
        id="PortraitVideo"
        component={ContinuousAudioVideo}
        durationInFrames={900}
        fps={FPS}
        width={1080}
        height={1920} // Portrait mode
      />
    </>
  );
};
