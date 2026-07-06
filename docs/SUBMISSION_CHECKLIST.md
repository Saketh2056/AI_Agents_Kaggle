# FINAL SUBMISSION CHECKLIST — do these in order

## 1. Push the code to GitHub (~10 min)
1. Go to https://github.com/new — name: `studybuddy-agent`, visibility:
   **Public**, do NOT add a README (we have one). Create.
2. In Terminal, from the project folder:
   ```bash
   cd ~/Documents/Code/Kaggle
   git add -A
   git commit -m "StudyBuddy: multi-agent AI study concierge (Kaggle ADK capstone)"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/studybuddy-agent.git
   git push -u origin main
   ```
   (GitHub will ask you to sign in the first time.)
3. Open the repo page and CHECK: there is **no `.env` file** anywhere
   (only `.env.example`). The `.gitignore` handles this, but verify with
   your own eyes.

## 2. Record the video (~1 hour) 
Follow `docs/VIDEO_SCRIPT.md` word for word. Upload to YouTube (Public).
Grab the landing-page screenshot for the cover image while you're at it.

## 3. Create the Kaggle Writeup (~20 min)
1. Competition page → **New Writeup**.
2. Copy everything from `docs/WRITEUP.md` (title/subtitle at the top; skip the
   comment lines starting with #).
3. Track: **Concierge Agents**.
4. Media gallery: attach the **cover image** + the **YouTube video link**.
5. Project link: your GitHub repo URL.
6. Save → then press **SUBMIT** (top right). A saved draft does NOT count.
7. Reload the page and confirm it shows as **Submitted**.

## Rules double-check (10 seconds each)
- [ ] Video ≤ 5 minutes, on YouTube, attached
- [ ] Cover image attached
- [ ] Writeup ≤ 2,500 words (ours ≈ 1,400)
- [ ] Repo public, README has setup steps
- [ ] NO API keys/passwords anywhere in the repo
- [ ] Submitted (not draft) BEFORE the deadline — don't cut it close
