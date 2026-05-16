# gdg-apl-host

Hackathon shell: Hotstar cricket on top, quiz strip on the bottom, one fullscreen window for the projector.

## Run

```
npm install
npm run dev
```

This starts Vite (quiz strip on :5173) and Electron (the shell window with Hotstar on top, quiz strip iframed at the bottom).

## Demo flow

1. In the Electron window, log in to Hotstar (mobile OTP). Session persists via the `persist:hotstar` partition.
2. Navigate the top pane to the live match.
3. Press `F11` to fullscreen onto the projector.
4. Use `→` / `Space` / `←` on the keyboard to advance between innings-1 and innings-2 challenges.

## Files

- `electron/main.cjs` — window + Chrome UA spoof for the Hotstar webview
- `shell.html` — grid layout: webview (top) + quiz iframe (bottom 22vh)
- `src/App.tsx` — quiz strip, keyboard-driven
- `src/challenges.json` — the two challenges, one per innings

## Notes

- Hotstar uses Widevine DRM; modern Electron ships with Widevine support, so the web player works inside `<webview>`. If it ever refuses to play, the UA spoof in `electron/main.cjs` is the first thing to check.
- This composites Hotstar's own player visually with our overlay — it does not extract or restream Hotstar's video.
