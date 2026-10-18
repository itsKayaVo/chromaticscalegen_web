# GitHub Pages site

The repository root contains the site files. `generator-config.js` is configured to use the Ubuntu audio service at `https://castrofamilyserver.tailba990e.ts.net`.

Audio samples selected on the site are sent to that server for processing with the original Praat/Parselmouth engine. The Ubuntu service must allow the exact origin of this GitHub Pages site in `CSGPR_ALLOWED_ORIGINS`; for a project site such as `https://ACCOUNT.github.io/PROJECT/`, the origin is `https://ACCOUNT.github.io`.

The repository includes a GitHub Actions workflow that deploys the root files to Pages when changes are pushed to `main`. In the repository settings, open **Pages** and set **Build and deployment > Source** to **GitHub Actions**.
