# Remotion Troubleshooting Guide

## Common Issues

| Issue | Cause | Solution |
|-------|-------|---------|
| **Audio cuts between slides** | Per-slide `<Audio>` in `<Sequence>` | Use single `<Audio>` at root level (continuous audio pattern) |
| **Audio ends early** | Frame calculation truncates instead of ceiling | Use `Math.ceil()` for all ms-to-frame conversions |
| **Silent gap between scenes** | Rounding error in start frame calculation | Add 200-300ms gap in concat_audio.py instead of zero gap |
| **Black/blank render** | Missing background or opacity = 0 | Check `backgroundColor` and initial `interpolate` values |
| **Module not found** | Missing dependencies | Run `rm -rf node_modules && npm install` |
| **Port already in use** | Previous dev server running | Kill process on port 3000: `npx kill-port 3000` |
| **Fonts missing in render** | Custom fonts not loaded | Use `@remotion/google-fonts` or `staticFile()` for local fonts |
| **Slow render** | Too many frames or heavy components | Reduce FPS, optimize components, use `useMemo` for calculations |
| **TailwindCSS not working** | Missing config or CSS import | Verify `remotion.config.ts` has enableTailwind, import `index.css` in Root |

## Audio Debugging Checklist

1. Is there ONE `<Audio>` component at the root level? (Not inside any `<Sequence>`)
2. Does `narration.mp3` exist in `public/audio/`?
3. Does the total `durationInFrames` of the composition >= audio duration in frames?
4. Are scene boundaries using `Math.ceil()` for frame calculations?
5. Run `python measure_audio.py public/audio/narration.mp3` to verify actual duration
6. Check Remotion Studio audio waveform - is there a continuous line?

## Performance Tips

1. **Use `useMemo`** for expensive calculations that don't change every frame
2. **Prefer `interpolate()`** over manual math - it handles edge cases
3. **Use `spring()`** for natural motion instead of linear easing
4. **Keep components small** - one component per scene
5. **Use TailwindCSS** for styling instead of heavy inline styles
6. **Optimize images** - compress before placing in `public/`
7. **Use `premountFor`** on heavy sequences to pre-load them

## Render Error Recovery

- "Composition not found": check ID matches exactly (case-sensitive)
- Render crashes: try `--gl=angle` on Windows, check memory (close other apps)
- Audio is silent: verify narration.mp3 exists in `public/audio/`
- Black frames: check component renders something for all frame ranges
- Very slow: use `--crf=28` for draft, reduce resolution, or limit frame range
