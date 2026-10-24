# GitHub Pages site

The repository root contains the site files. `generator-config.js` is configured to use the Ubuntu audio service at `https://castrofamilyserver.tailba990e.ts.net`.

Audio samples selected on the site are sent to that server for processing with the original Praat/Parselmouth engine. The Ubuntu service must allow the exact origin of this GitHub Pages site in `CSGPR_ALLOWED_ORIGINS`; for a project site such as `https://ACCOUNT.github.io/PROJECT/`, the origin is `https://ACCOUNT.github.io`.

Enable **Also create an SF2 instrument for FL Studio Mobile** to download `chromatic.wav` and `chromatic.sf2` together. The SF2 bank maps each generated semitone. Its lowest sample also covers MIDI keys below the generated range, and its highest sample covers keys above it; SoundFont Player transposes those edge samples. Load the bank in FL Studio Mobile 4.10 or newer with SoundFont Player. The SF2 writer source is in `soundfont_sf2.py`; the Ubuntu service uses this module when creating the ZIP.

The repository includes a GitHub Actions workflow that deploys the root files to Pages when changes are pushed to `main`. In the repository settings, open **Pages** and set **Build and deployment > Source** to **GitHub Actions**.

The generator shows upload progress, then an explicit processing status while the server builds the audio, followed by download progress. Keep the page open until the result finishes.
