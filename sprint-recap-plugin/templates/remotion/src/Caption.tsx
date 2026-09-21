import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

/**
 * The on-screen step text.
 *
 * This caption is the same string that appears as the numbered instruction in
 * the HTML reproduction guide -- both read it from the step script, so the
 * video can never describe a step differently from the written guide.
 */

const ARABIC = /[؀-ۿ]/;

export const Caption: React.FC<{
  text: string;
  workItem?: number | string;
  role?: string;
  index?: number;
  total?: number;
  start?: string;
}> = ({ text, workItem, role, index, total, start }) => {
  const frame = useCurrentFrame();
  const { fps, height } = useVideoConfig();

  const enter = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 14 });
  const y = interpolate(enter, [0, 1], [60, 0]);
  const rtl = ARABIC.test(text);

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: Math.round(height * 0.055),
        display: "flex",
        justifyContent: "center",
        transform: `translateY(${y}px)`,
        opacity: enter,
      }}
    >
      <div
        dir={rtl ? "rtl" : "ltr"}
        style={{
          maxWidth: "86%",
          padding: "18px 28px",
          borderRadius: 14,
          background: "rgba(9, 12, 20, 0.88)",
          border: "1px solid rgba(255,255,255,0.14)",
          boxShadow: "0 18px 45px rgba(0,0,0,0.45)",
          color: "#f5f7fb",
          fontFamily:
            "Segoe UI, Inter, system-ui, -apple-system, 'Noto Sans Arabic', sans-serif",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 8,
            fontSize: 20,
            color: "#8ab4ff",
            flexDirection: rtl ? "row-reverse" : "row",
          }}
        >
          {workItem ? (
            <span
              style={{
                background: "rgba(138,180,255,0.16)",
                border: "1px solid rgba(138,180,255,0.35)",
                borderRadius: 999,
                padding: "2px 12px",
                fontWeight: 600,
              }}
            >
              #{workItem}
            </span>
          ) : null}
          {index && total ? (
            <span style={{ opacity: 0.85 }}>
              Step {index} of {total}
            </span>
          ) : null}
          {role ? <span style={{ opacity: 0.6 }}>as {role}</span> : null}
          {start ? (
            <span style={{ opacity: 0.5, fontFamily: "Consolas, monospace" }}>
              {start}
            </span>
          ) : null}
        </div>
        <div style={{ fontSize: 34, lineHeight: 1.28, fontWeight: 600 }}>{text}</div>
      </div>
    </div>
  );
};
