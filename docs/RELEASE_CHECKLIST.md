# Release Checklist — VideoMind Agent

## 1. Privacy Check

- [ ] Run `python scripts/check_experiment_privacy.py --root . --include-json --include-md`
- [ ] No Windows absolute paths in API responses or docs
- [ ] No API keys or tokens in committed files
- [ ] No email addresses in committed files
- [ ] `.env` not tracked by git (check `.gitignore`)
- [ ] `data/` not tracked by git
- [ ] `logs/` not tracked by git
- [ ] `__pycache__/` not tracked by git

## 2. Test Check

- [ ] Backend compile: `python -m compileall backend/app scripts`
- [ ] Backend pytest: `cd backend && pytest -ra -q` — all passed
- [ ] Frontend typecheck: `cd frontend && npm run typecheck` — 0 errors
- [ ] Frontend tests: `cd frontend && npm run test:run` — all passed
- [ ] Frontend build: `cd frontend && npm run build` — success

## 3. Build Check

- [ ] `frontend/dist/` is up-to-date after `npm run build`
- [ ] No TypeScript errors in production build
- [ ] Vite build produces no warnings

## 4. Demo Check

- [ ] Backend starts without errors: `.\dev.ps1 -NoFrontend`
- [ ] Frontend starts without errors
- [ ] Upload flow works
- [ ] Analysis pipeline completes
- [ ] Result API returns valid JSON
- [ ] VideoPlayer loads source video
- [ ] Timeline shows highlights
- [ ] Clip playback works
- [ ] Reports render correctly

## 5. Documentation Check

- [ ] README.md is up-to-date
- [ ] docs/portfolio is complete
- [ ] docs/demo/DEMO_SCRIPT.md reflects current behavior
- [ ] docs/demo/DEMO_CHECKLIST.md is actionable
- [ ] docs/HANDOFF_NOTES.md reflects current architecture
- [ ] docs/ROADMAP_FINAL.md has correct status
- [ ] All URLs in docs are valid (relative paths)

## 6. Git State Check

- [ ] No local absolute paths in any tracked file
- [ ] `.env.example` contains no real secrets
- [ ] `.gitignore` covers all build artifacts
- [ ] All changes are intentional and reviewed

## 7. Delivery Package Contents

```
videomind-agent/
├── backend/           # FastAPI backend (380 tests passing)
├── frontend/          # React + Vite frontend (275 tests passing)
├── scripts/
│   ├── check_all.ps1
│   ├── verify_mvp_delivery.py
│   └── check_experiment_privacy.py
├── docs/
│   ├── demo/
│   │   ├── DEMO_SCRIPT.md
│   │   ├── DEMO_CHECKLIST.md
│   │   └── SCREENSHOT_GUIDE.md
│   ├── portfolio/
│   └── HANDOFF_NOTES.md
│   └── ROADMAP_FINAL.md
├── dev.ps1
├── README.md
├── .env.example
└── .gitignore
```
