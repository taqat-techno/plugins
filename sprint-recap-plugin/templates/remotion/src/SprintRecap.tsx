import React from "react";
import {
  AbsoluteFill,
  Audio,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Caption } from "./Caption";
import data from "./data.json";

type Scene = {
  type: "title" | "item" | "step" | "outro";
  durationInFrames: number;
  title?: string;
  subtitle?: string;
  caption?: string;
  clip?: string;
  audio?: string;
  workItem?: number;
  parent?: number | null;
  role?: string;
  start?: string;
  index?: number;
  total?: number;
  stepCount?: number;
};

const BG = "#0b0f17";
const FONT =
  "Segoe UI, Inter, system-ui, -apple-system, 'Noto Sans Arabic', sans-serif";

const Card: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 18 });
  const scale = interpolate(enter, [0, 1], [0.94, 1]);
  return (
    <AbsoluteFill
      style={{
        background: BG,
        alignItems: "center",
        justifyContent: "center",
        fontFamily: FONT,
        color: "#f5f7fb",
      }}
    >
      <div style={{ transform: `scale(${scale})`, opacity: enter, textAlign: "center" }}>
        {children}
      </div>
    </AbsoluteFill>
  );
};

const TitleScene: React.FC<Scene> = ({ title, subtitle }) => (
  <Card>
    <div style={{ fontSize: 68, fontWeight: 700, letterSpacing: -1 }}>{title}</div>
    {subtitle ? (
      <div style={{ fontSize: 30, marginTop: 18, opacity: 0.66 }}>{subtitle}</div>
    ) : null}
  </Card>
);

const ItemScene: React.FC<Scene> = ({ workItem, title, parent, role, stepCount }) => (
  <Card>
    <div
      style={{
        display: "inline-block",
        padding: "6px 20px",
        borderRadius: 999,
        background: "rgba(138,180,255,0.16)",
        border: "1px solid rgba(138,180,255,0.35)",
        color: "#8ab4ff",
        fontSize: 26,
        fontWeight: 600,
      }}
    >
      #{workItem}
    </div>
    <div style={{ fontSize: 50, fontWeight: 700, marginTop: 22, maxWidth: 1000 }}>
      {title}
    </div>
    <div style={{ fontSize: 24, marginTop: 18, opacity: 0.6 }}>
      {parent ? `PBI #${parent}` : null}
      {parent && role ? "  ·  " : null}
      {role ? `as ${role}` : null}
      {stepCount ? `  ·  ${stepCount} step${stepCount > 1 ? "s" : ""}` : null}
    </div>
  </Card>
);

const StepScene: React.FC<Scene> = (scene) => (
  <AbsoluteFill style={{ background: BG }}>
    {scene.clip ? (
      <OffthreadVideo src={staticFile(scene.clip)} style={{ width: "100%", height: "100%" }} />
    ) : null}
    {scene.audio ? <Audio src={staticFile(scene.audio)} /> : null}
    <Caption
      text={scene.caption ?? ""}
      workItem={scene.workItem}
      role={scene.role}
      index={scene.index}
      total={scene.total}
      start={scene.start}
    />
  </AbsoluteFill>
);

const renderScene = (scene: Scene) => {
  switch (scene.type) {
    case "title":
    case "outro":
      return <TitleScene {...scene} />;
    case "item":
      return <ItemScene {...scene} />;
    case "step":
      return <StepScene {...scene} />;
    default:
      return null;
  }
};

export const SprintRecap: React.FC = () => {
  let offset = 0;
  return (
    <AbsoluteFill style={{ background: BG }}>
      {(data.scenes as Scene[]).map((scene, i) => {
        const from = offset;
        offset += scene.durationInFrames;
        return (
          <Sequence
            key={i}
            from={from}
            durationInFrames={scene.durationInFrames}
            name={`${scene.type}-${scene.workItem ?? i}`}
          >
            {renderScene(scene)}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
