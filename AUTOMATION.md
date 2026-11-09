# Daily Short – instructions for the scheduled run

Every day a fresh Claude session creates one new English "crazy facts" Short and schedules it
on YouTube via Metricool for **13:00 Europe/Berlin**.

1. Setup (fresh container):
   `apt-get install -y fonts-noto-color-emoji ffmpeg`, `pip install piper-tts numpy pillow`,
   `mkdir -p voices && curl -sL https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-en-us-ryan-high.tar.gz | tar xz -C voices`
2. Pick a NEW topic: list `stories/` and never repeat a topic. Use a true, well-documented,
   surprising fact or real story (history, animals, science, everyday life). Check the facts
   with a web search; avoid anything you cannot verify. Keep it family friendly.
3. Write `stories/YYYY-MM-DD-slug.json` in the same format as the existing stories:
   6–8 scenes, 25–45 s spoken, scene 1 = strong hook, last scene = `{"anim": "subscribe"}`.
   Available anims: pop (1–3 emoji), count (number counter, needs `to`, `label`, `emoji`, `under`),
   shake (2 emoji + explosions), run (`emoji` runs across, `trail`), rain (2 emoji + falling `drop`),
   zoom (`emoji` [main, accent], `orbit`), subscribe. Only use emoji that render with Noto Color
   Emoji (no flags or multi-codepoint sequences). Vary the anims.
4. Render: `python3 make_short.py stories/<file>.json videos/<file>.mp4`, then extract 3–4 frames
   with ffmpeg and look at them to check the captions and emoji look right.
5. Commit the story JSON (NOT the mp4) to `main` and push.
6. `./publish_video.sh videos/<file>.mp4` → prints the public URL.
7. Metricool `createScheduledPost`: blogId 7978983, provider youtube, date today 13:00
   Europe/Berlin, media [URL], youtubeData {title (≤ 70 chars, ends with " #shorts"),
   type "short", privacy "public", tags, category "EDUCATION", madeForKids false,
   isAiGeneratedContent false}, text = description with hashtags.
   If 13:00 has already passed, schedule 15 minutes from now.
