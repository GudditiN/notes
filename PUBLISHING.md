# Publishing this course on GitBook

This folder is a ready-to-sync GitBook space. GitBook reads `.gitbook.yaml`, builds the sidebar from `SUMMARY.md`, and serves images from `.gitbook/assets/`.

## 1. Push it to GitHub

```bash
cd docker-kubernetes-from-scratch
git init
git add .
git commit -m "Docker & Kubernetes from Scratch course"
git branch -M main
git remote add origin https://github.com/GudditiN/docker-kubernetes-from-scratch.git
git push -u origin main
```

## 2. Connect GitBook

1. In GitBook, create a new **space** (or open an empty one).
2. Choose **Configure → GitHub Sync**, install the GitBook GitHub app, and pick this repository and the `main` branch.
3. Choose **GitHub → GitBook** for the initial sync so the repository content is imported.
4. Wait for the first sync. The sidebar should show Docker essentials, Kubernetes foundations, Running real workloads, Operating in production, Capstone project and Reference.

## 3. Make it look finished

- **Customize → Theme:** primary color `#326CE5`, tint the background, and pick a clean font (Inter works well with the diagrams).
- **Customize → Logo:** upload `.gitbook/assets/logo.svg`.
- **Customize → Icon:** use the ⎈ helm emoji or upload your own.
- **Publish → Share to the web** (public or with a password). You can add a custom domain later under the site settings.

## 4. Editing later

Edit the Markdown here and push, or edit in GitBook and let it commit back. Both directions stay in sync.

## Notes

- Page icons use Font Awesome names in each page's front matter (`icon: terminal`). Change them freely.
- Diagrams are standalone SVGs with a white card background, so they read well in both light and dark mode.
- `notes-project/` holds every capstone file (app, Dockerfile, compose.yaml, manifests, `setup.sh`). GitBook ignores it; it's there for learners who clone the repo.
- If a code sample with Helm or GitHub Actions `{{ ... }}` expressions ever renders oddly after an edit in the GitBook editor, re-sync from Git; the Markdown here is the source of truth.
