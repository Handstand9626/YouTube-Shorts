# YouTube-Shorts

Daily animated "crazy facts" Shorts.

- `make_short.py` – renders a 1080x1920 Short from a story JSON (Piper neural voice, animated emoji scenes, kinetic captions, music and sound effects).
- `stories/` – one JSON per video (title, description, tags, scenes).
- `videos/` – rendered videos, served publicly so Metricool can pick them up.

## Setup

```bash
sudo apt-get install -y fonts-noto-color-emoji ffmpeg
pip install piper-tts numpy pillow
mkdir -p voices && curl -sL https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-en-us-ryan-high.tar.gz | tar xz -C voices
```

## Render

```bash
python3 make_short.py stories/2026-11-09-emu-war.json videos/2026-11-09-emu-war.mp4
```

## Erklärvideo: Energiegewinnung im Mitochondrium

`mitochondrien/make_video.py` rendert ein 16:9-Erklärvideo (ca. 4:25 min, zwei Sprecher) zu Redoxreaktionen, NADH und ATP –
einmal mit KI-Stimmen und einmal nur mit Musik und Untertiteln zum Selbst-Einsprechen. Der Sprechertext steht in `mitochondrien/SKRIPT.md`.

```bash
for v in thorsten kerstin; do curl -sL https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-de-$v-low.tar.gz | tar xz -C voices; done
python3 mitochondrien/make_video.py videos
```
