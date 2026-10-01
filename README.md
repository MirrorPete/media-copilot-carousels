# Media Copilot carousels

Public hosting for The Media Copilot's text carousels (Instagram image sets and LinkedIn PDF documents). Buffer fetches the files from this repo at post time, so nothing here is renamed or deleted until its posts have gone out.

Layout:

- `sets/<column-date>-<slug>/slide-NN.png` and `carousel.pdf`: one folder per carousel, plus the `slides.json` it was rendered from.
- `tools/build_carousel.py`: renders a `slides.json` to PNGs and a PDF with headless Chromium (Playwright). `tools/check.py` verifies numbers, names and banned words against the column text.
- `tools/fonts/`: Oswald and Inter (from the fontsource npm packages).

Files are served at `https://raw.githubusercontent.com/MirrorPete/media-copilot-carousels/main/<path>`.

The rules for writing a set live in the Media Copilot Social Media Management Project (07-carousel-spec.md).
