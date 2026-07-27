# Problem reports

The bridge exposes one producer-owned problem-report flow:

1. `POST /v1/feedback/draft` creates an immutable local preview.
2. The person reviews the public warning, free-form description and optional transcript.
3. `POST /v1/feedback/submit` requires `confirmed: true`.

The conversational `report-problem` skill performs step 1 only. It cannot publish an issue.
The transcript option defaults to on, but contains only visible user messages and final assistant
answers. Hidden prompts, progress, tool output and credentials are excluded.

Configure the public destination with
`CODEX_NATIVE_FEEDBACK_CONFIG=~/.config/idlisseus/feedback.json`:

```json
{
  "repository": "organisation/public-reports",
  "web_url": "https://github.com",
  "api_url": "https://api.github.com",
  "labels": ["user-report"],
  "token_file": "/run/secrets/github-issues-token"
}
```

Do not put a token in this file or in the repository. Without `token_file`, confirmed submission
returns a pre-filled GitHub issue URL so the browser can perform the final authenticated action.

Draft request:

```json
{
  "session_id": "visible-chat-id",
  "description": "The visual used the wrong broad reading.",
  "include_conversation": true,
  "transcript": [
    {"role": "user", "content": "Show all recorded examples"},
    {"role": "assistant", "content": "Which example should I use?"}
  ]
}
```

The consumer should show a persistent “Report a problem” action, make it more prominent after a
blocked or contradictory result, collect free-form text, leave “Include this conversation” on by
default, show the public warning and full preview, then require a separate confirmation.
