# Voice Reference for Remotion Videos

## edge-tts (FREE - No API Key)

300+ voices across 70+ languages. Completely free, uses Microsoft Neural TTS.

### Popular English Voices

| Voice | Gender | Accent | Best For |
|-------|--------|--------|----------|
| `en-US-AriaNeural` | Female | American | General narration |
| `en-US-GuyNeural` | Male | American | Professional tone |
| `en-GB-RyanNeural` | Male | British | Formal presentations |
| `en-GB-SoniaNeural` | Female | British | Elegant narration |
| `en-AU-NatashaNeural` | Female | Australian | Casual tone |
| `en-IN-NeerjaNeural` | Female | Indian | Tech presentations |

### Arabic Voices

| Voice | Gender | Dialect |
|-------|--------|---------|
| `ar-SA-HamedNeural` | Male | Saudi |
| `ar-SA-ZariyahNeural` | Female | Saudi |
| `ar-EG-SalmaNeural` | Female | Egyptian |
| `ar-EG-ShakirNeural` | Male | Egyptian |

### Rate and Pitch Control

```bash
# Slower speech (good for tutorials)
edge-tts --text "Speak slowly" --voice "en-US-AriaNeural" --rate="-20%" --write-media slow.mp3

# Faster speech (good for recaps)
edge-tts --text "Speak fast" --voice "en-US-AriaNeural" --rate="+15%" --write-media fast.mp3

# Higher pitch
edge-tts --text "Higher voice" --voice "en-US-GuyNeural" --pitch="+10Hz" --write-media high.mp3

# Lower pitch
edge-tts --text "Lower voice" --voice "en-US-GuyNeural" --pitch="-10Hz" --write-media low.mp3
```

### SSML Support (Advanced)

```xml
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
  <voice name="en-US-AriaNeural">
    Welcome to our presentation.
    <break time="500ms"/>
    Today we will cover three important topics.
    <emphasis level="strong">First</emphasis>, the architecture overview.
  </voice>
</speak>
```

## Voice Script Writing Tips

### For Natural Narration

1. **Write conversationally** - avoid jargon, use simple sentences
2. **One idea per sentence** - easier for TTS to pace correctly
3. **Add natural pauses** - use periods and commas, not ellipses
4. **Keep scenes 10-30 seconds** - long monologues lose attention
5. **End scenes with complete thoughts** - don't split sentences across slides

### Timing Guide

| Content Type | Approximate Duration |
|-------------|---------------------|
| Title slide (just a name) | 2-3 seconds |
| Single sentence | 3-5 seconds |
| Paragraph (3-4 sentences) | 10-15 seconds |
| Detailed explanation | 20-30 seconds |
| Full presentation (10 slides) | 3-7 minutes |

## ElevenLabs (Premium - Optional)

Ultra-realistic voices with character-level timestamps. Requires API key.

```bash
npm install @elevenlabs/elevenlabs-js
```

```typescript
import { ElevenLabsClient } from "@elevenlabs/elevenlabs-js";

const client = new ElevenLabsClient({ apiKey: process.env.ELEVENLABS_API_KEY });

const result = await client.textToSpeech.convertWithTimestamps("voice-id", {
  text: "Your narration text here",
  model_id: "eleven_multilingual_v2",
});
```
