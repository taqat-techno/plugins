import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
// The captured clips are VP8/WebM from Playwright; H.264 output plays anywhere
// a stakeholder is likely to open it.
Config.setCodec("h264");
