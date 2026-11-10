# Daily Shorts – instructions for the scheduled runs

The scheduled task runs **twice a day**. Each run creates ONE new English "crazy facts" Short
and schedules it on YouTube via Metricool:

| Run starts (Europe/Berlin) | Publish slot |
|---|---|
| before 13:00 | **13:00** today |
| 13:00 or later | **19:00** today |

## 0. Duplicate check (always first)
Call Metricool `getScheduledPosts` (brandId 7978983, timezone Europe/Berlin, today 00:00–23:59,
extendedRange true). If a YouTube post already exists for your slot (13:00 or 19:00 today),
STOP and report "Slot already filled" – do not create a second video.

## 1. Setup (fresh container)
- `apt-get install -y fonts-noto-color-emoji ffmpeg`
- `python3 -m pip install piper-tts numpy pillow` (install with the SAME python3 you run
  make_short.py with; check `python3 -c "import numpy, piper"`)
- `mkdir -p voices && curl -sL https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-en-us-ryan-high.tar.gz | tar xz -C voices`

## 2. Topic and research (quality matters most)
- List `stories/` and never repeat a topic. Vary categories day to day: history, animals,
  space, human body, science, geography, food, inventions, everyday objects, record holders.
- Pick a fact that makes people say "wait, what?" – surprising, concrete, easy to picture.
- Research it with WebSearch BEFORE writing: confirm every number, date and name with at
  least two reliable sources (encyclopedias, museums, universities, NASA/NOAA, major news,
  peer-reviewed summaries). Drop or soften anything you cannot verify ("about", "around").
  Do NOT rely on memory alone. No myths, no "people only use 10% of their brain" style
  falsehoods, nothing gory, political or about living private persons.
- Collect 2–3 extra specific details (numbers, names, comparisons) that make it richer.

## 3. Story structure (`stories/YYYY-MM-DD-slug.json`, same format as existing stories)
7–9 scenes, 35–50 s spoken in total, simple spoken English, short sentences.
1. **Hook** (anim `title`, with `headline` of 2–3 short lines in CAPS, `emoji` 1–2):
   the most surprising claim in one sentence.
2. **Context** – who/what/when.
3. **3–4 detail scenes** with concrete numbers and comparisons ("that's taller than…").
4. **Twist / payoff** – the "why" or an extra surprising consequence.
5. **Subscribe** – `{"text": "Subscribe for a new crazy fact every day!", "anim": "subscribe"}`.

Also fill in: `title` (≤ 70 chars, ends with " #shorts"), `description` (2–4 sentences with
the key numbers + a "Sources:" line naming the sources + hashtags), `tags`, and `comment`
(a question that invites replies, posted as the first comment).

### Available scene animations – use at least 5 different ones per video
- `title`: hook card. Fields: `headline` ("LINE1\nLINE2"), `emoji` [1–2].
- `stat`: big number counter. `to` (number), optional `prefix`, `suffix`, `decimals`,
  `label` (short CAPS), `emoji` [1–2].
- `timeline`: `points` [{"year", "label", "emoji"}] (2–4 points), optional `gap` text.
- `versus`: `sides` [{"emoji", "label", "value"}, {...}] – comparisons.
- `pop`: 1–3 `emoji` bounce in.
- `count`: counter + swarm: `to`, `label`, `emoji` [one], `under` (ground emoji).
- `shake`: 2 `emoji` + explosions + camera shake (dramatic moments).
- `run`: `emoji` [one] races across, `trail` emoji (speed).
- `rain`: 2 `emoji` + falling `drop` emoji.
- `zoom`: `emoji` [main, accent], `orbit` emoji circling (reveals / winners).
- `subscribe`: end card.
Only use emoji that render with Noto Color Emoji (no flags, no skin-tone or ZWJ sequences).
Keep labels short; the renderer shrinks text to fit but shorter reads better.

## 4. Render and check
`python3 make_short.py stories/<file>.json videos/<file>.mp4`, then extract one frame from
the middle of EVERY scene with ffmpeg and look at them. Fix and re-render if any text is
cut off, overlaps, or an emoji is missing (shows a box).

## 5. Publish
1. Commit the story JSON (NOT the mp4) to `main` and push.
2. `./publish_video.sh videos/<file>.mp4` → prints the public URL.
3. Metricool `createScheduledPost`: blogId 7978983, provider youtube, date = your slot today
   (Europe/Berlin), media [URL], firstCommentText = story `comment`, text = description,
   youtubeData {title, type "short", privacy "public", tags, category "EDUCATION",
   madeForKids false, isAiGeneratedContent false}.
   If the slot time has already passed, schedule 15 minutes from now.
