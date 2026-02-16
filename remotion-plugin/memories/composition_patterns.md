# Composition Patterns for Remotion Videos

## Pattern Reference

### 1. Title Slide

```typescript
const TitleSlide: React.FC<{ title: string; subtitle?: string }> = ({ title, subtitle }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const translateY = interpolate(frame, [0, 20], [30, 0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: "#0f172a", justifyContent: "center", alignItems: "center" }}>
      <h1 style={{ color: "#fff", fontSize: 72, opacity, transform: `translateY(${translateY}px)` }}>
        {title}
      </h1>
      {subtitle && (
        <p style={{ color: "#94a3b8", fontSize: 28, opacity: interpolate(frame, [15, 35], [0, 1], { extrapolateRight: "clamp" }) }}>
          {subtitle}
        </p>
      )}
    </AbsoluteFill>
  );
};
```

### 2. Bullet Points (Staggered Reveal)

```typescript
const BulletSlide: React.FC<{ title: string; points: string[] }> = ({ title, points }) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ backgroundColor: "#1e293b", padding: 80, justifyContent: "center" }}>
      <h2 style={{ color: "#fff", fontSize: 48, marginBottom: 40 }}>{title}</h2>
      {points.map((point, i) => {
        const delay = 15 + i * 12;
        const op = interpolate(frame, [delay, delay + 12], [0, 1], {
          extrapolateLeft: "clamp", extrapolateRight: "clamp",
        });
        return (
          <div key={i} style={{ opacity: op, marginBottom: 18, display: "flex", gap: 14 }}>
            <span style={{ color: "#3b82f6" }}>-</span>
            <span style={{ color: "#e2e8f0", fontSize: 26 }}>{point}</span>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
```

### 3. Image with Ken Burns (Zoom)

```typescript
const ImageSlide: React.FC<{ image: string; caption: string }> = ({ image, caption }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const zoom = interpolate(frame, [0, durationInFrames], [1, 1.1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill>
      <Img src={staticFile(image)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${zoom})` }} />
      <AbsoluteFill style={{ background: "linear-gradient(transparent 60%, rgba(0,0,0,0.7))", justifyContent: "flex-end", padding: 60 }}>
        <h2 style={{ color: "#fff", fontSize: 36 }}>{caption}</h2>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
```

### 4. Scene Transition Wrapper

```typescript
const SceneTransition: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const enter = spring({ frame, fps, config: { damping: 200, stiffness: 100 } });
  const exit = interpolate(frame, [durationInFrames - 10, durationInFrames], [1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ opacity: exit, transform: `scale(${enter})` }}>
      {children}
    </AbsoluteFill>
  );
};
```

### 5. Counter/Number Animation

```typescript
const Counter: React.FC<{ target: number; label: string }> = ({ target, label }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progress = spring({ frame, fps, config: { damping: 100, stiffness: 50 } });
  const value = Math.round(target * progress);

  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontSize: 96, fontWeight: 700, color: "#3b82f6" }}>{value}</div>
      <div style={{ fontSize: 24, color: "#94a3b8", marginTop: 8 }}>{label}</div>
    </div>
  );
};
```

### 6. Progress Bar

```typescript
const ProgressBar: React.FC<{ progress: number }> = ({ progress }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const width = spring({ frame, fps, config: { damping: 100 } }) * progress;

  return (
    <div style={{ width: "80%", height: 12, backgroundColor: "#334155", borderRadius: 6, overflow: "hidden" }}>
      <div style={{ width: `${width}%`, height: "100%", backgroundColor: "#3b82f6", borderRadius: 6 }} />
    </div>
  );
};
```

## Color Schemes

### Dark Professional
```
background: #0f172a (slate-900)
surface:    #1e293b (slate-800)
text:       #f8fafc (slate-50)
muted:      #94a3b8 (slate-400)
accent:     #3b82f6 (blue-500)
```

### Light Clean
```
background: #ffffff
surface:    #f8fafc (slate-50)
text:       #0f172a (slate-900)
muted:      #64748b (slate-500)
accent:     #2563eb (blue-600)
```

### Brand (Customize)
```
background: #[your-dark]
surface:    #[your-medium]
text:       #[your-light]
accent:     #[your-brand-color]
```

## Resolution Presets

| Use Case | Width | Height | FPS |
|----------|-------|--------|-----|
| YouTube/Presentation | 1920 | 1080 | 30 |
| Instagram Reels/TikTok | 1080 | 1920 | 30 |
| Instagram Square | 1080 | 1080 | 30 |
| 4K | 3840 | 2160 | 30 |
| Twitter | 1280 | 720 | 30 |
