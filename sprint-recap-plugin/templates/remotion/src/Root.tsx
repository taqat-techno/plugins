import React from "react";
import { Composition } from "remotion";
import { SprintRecap } from "./SprintRecap";
import data from "./data.json";

/**
 * Dimensions and duration come from data.json, which the build stage writes
 * from the capture log. Nothing here is hand-tuned per sprint.
 */
export const RemotionRoot: React.FC = () => (
  <Composition
    id="SprintRecap"
    component={SprintRecap}
    durationInFrames={data.durationInFrames}
    fps={data.fps}
    width={data.width}
    height={data.height}
  />
);
