# ✨📝 Groq ALM API - Transcribe

Transcribes an audio file to text using Whisper on Groq's API.

## Setup

Same as the other Groq nodes: put `GROQ_API_KEY=your_key_here` in the pack's
`.env` file and restart ComfyUI.

## Inputs

- **model** — Which Whisper model to use. The turbo model is fastest; the
  `distil-...-en` model is English-only.
- **file_path** — Path to the audio file. Supported: mp3, mp4, mpeg, mpga, m4a,
  wav, webm.
- **preset** — A saved prompt to steer spelling and style, or the default
  entry.
- **user_input** — Optional hint text, substituted into the preset where it
  contains `[user_input]`.

Advanced:

- **response_format** — What you get back:
  - `text` — one block of plain text
  - `text_with_linebreaks` — one line per detected segment
  - `text_with_timestamps` — each line prefixed `[MM:SS.mmm]`
  - `json` / `verbose_json` — the API response as formatted JSON
- **temperature** — Higher lets Whisper guess more freely on unclear audio.
- **language** — ISO 639-1 code of the spoken language, e.g. `en`, `fr`, `sv`.
- **max_retries** — Attempts before giving up.

## Outputs

- **transcription_result** — The transcription, in the chosen format.
- **success** — False on any error.
- **status_code** — HTTP status, e.g. `200 OK`.

## Notes

A missing file or an unsupported extension is caught before any request is
made, and returns `400 Bad Request` with the reason in the console. The
timestamp and line-break formats are built from the API's verbose response, so
they cost the same as `verbose_json`.
