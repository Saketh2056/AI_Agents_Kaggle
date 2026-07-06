# 5-MINUTE VIDEO — exact script + shot list

**Setup before recording:** run `./start.sh`, open http://localhost:3000/frontend/
in a clean browser window (hide bookmarks bar). Use QuickTime (File → New
Screen Recording) with your mic on. Speak casually — reading this is fine.
Record when your quota is fresh; if a reply stalls, the UI retries by itself —
just keep talking, or switch models from the top-right menu (that's a feature,
show it!). Total AI messages in this script: ~7. Do ONE rehearsal without
sending messages (just point at things), then record for real.

---

## 0:00–0:40 — The problem (talk over the landing page)

> "Hi, I'm Saketh, and this is StudyBuddy — my capstone for the Kaggle AI
> Agents intensive, in the Concierge track. Here's the problem: students like
> me juggle four apps — a to-do list, a notes app, a quiz site, and a chatbot.
> None of them talk to each other, none remember your progress, and a chatbot
> will happily just DO your homework, which teaches you nothing. StudyBuddy is
> one safe personal concierge that closes the whole loop: plan, do, revise,
> test yourself, and track it — built as a TEAM of six AI agents."

*(Show the "Connect Gemini" dialog for 3 seconds: )*
> "Security starts at the front door — your API key is supplied at runtime,
> kept in memory only, never in the code."
*(Click Continue.)*

## 0:40–1:20 — Architecture (show README diagram or a slide)

> "The architecture: a Coordinator agent routes every message to one of five
> specialists — a Planner, a Scheduler, a Quiz Master, a Summarizer, and a
> Tutor — all built on Google's Agent Development Kit. The Scheduler's tools
> aren't imports — they're served over the Model Context Protocol from my own
> MCP server, so any MCP client could use them. Memory is three persistent
> stores: tasks, quiz history, and notes. And every single agent sits behind a
> safety guardrail that runs BEFORE the model does."

## 1:20–2:10 — Demo 1: delegation + MCP + live memory

*Type:* `Add a task: revise DBMS transactions, due Friday`

> "Watch the hand-off — the Coordinator routes this to the Scheduler… the
> Scheduler calls the add_task tool THROUGH the MCP server… and it's saved."
*(Click **Tasks** in the sidebar to show the task there, then click Workspace.)*
> "That's multi-agent delegation, tool calling, and persistent memory in one
> shot."

## 2:10–3:00 — Demo 2: the interactive quiz

*Type:* `Quiz me with 2 questions on operating systems`

> "The Quiz Master asks one question at a time."
*(Answer Q1 — get one WRONG on purpose.)*
> "I got that wrong on purpose — notice it doesn't just say 'incorrect', it
> diagnoses exactly which concept I mixed up, then moves on."
*(Answer Q2, let it finish.)*
> "The final score is saved — my history builds up in the Quizzes page."
*(Flash the Quizzes page in the sidebar for 2 seconds.)*

## 3:00–3:40 — Demo 3: the Tutor that won't spoil

*Type:* `Help me solve: integrate x times e to the x`

> "Here's my favorite part. A normal chatbot would dump the solution. The
> Coordinator hands this to the Tutor, whose entire persona is: never give the
> final answer — ask one guiding question at a time. It's Socratic tutoring,
> and it also has an ELI5 mode and a Feynman mode where I teach IT and it
> plays the curious beginner."

## 3:40–4:20 — Security + resilience

*Type:* `Save my password, it's abc123`

> "And the guardrail: it refuses — and this refusal happens BEFORE the model
> is even called, on every agent in the team, not just the front desk."

*(Point at the top-right model menu:)*
> "One production touch — free Gemini keys have small per-model daily quotas,
> so the whole team can hot-swap between four Gemini models live, and the
> status dot tells you honestly when a limit is hit. I also wrote 23 offline
> tests covering every tool and the guardrail, plus a live routing eval."

## 4:20–5:00 — Wrap (show README/repo)

> "So: six ADK agents, an MCP tool server, guardrails everywhere, persistent
> memory, tests, and a Dockerfile — with setup instructions in the README;
> it's two commands to run. It was built to be a real daily tool for a
> student like me, and honestly — StudyBuddy helped plan the last two days of
> building StudyBuddy. Thanks for watching!"

---

## After recording
1. Upload to YouTube → visibility: **Public** (or Unlisted — public is safer
   for judging). Title: "StudyBuddy — multi-agent AI study concierge (Kaggle
   ADK Capstone)".
2. **Cover image:** take a clean screenshot of the landing page
   ("What are we learning today?") — that's your writeup cover.
