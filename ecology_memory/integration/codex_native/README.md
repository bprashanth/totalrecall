# Codex CLI + native skills in Idlisseus

This is the interactive form of the strongest `late-bound-skills` benchmark arm. Idlisseus is
the frontend and session transport; one resumable Codex CLI thread does skill discovery,
invocation, recovery and answer synthesis.

```text
Idlisseus browser/API
  -> OpenAI-compatible bridge on :7011
  -> Codex CLI, GPT-5.4 medium
  -> frozen skill index + SKILL.md procedures
  -> allowlisted skill gateway
  -> deterministic ecology executor/connectors
  -> compact visible trace + final answer
```

The bridge emits skill discovery, skill reads, invocations, result summaries, calculations and
Codex progress as ordinary streamed response text. This lets the unmodified Idlisseus frontend
show the audit immediately. Complete Codex JSONL and full skill results remain in the server-side
audit directory named at the top and bottom of each response.

## Start and register

Use the Idlisseus virtual environment because the semantic-literature connector needs its
`fastembed` dependency:

```bash
cd /home/beeps/src/github.com/bprashanth/totalrecall

/home/beeps/src/github.com/bprashanth/idlisseus/chatbots/odysseus/venv/bin/python \
  ecology_memory/integration/codex_native/setup_idlisseus.py start
```

The setup command starts the local bridge, generates a mode-0600 bridge token, and registers this
shared Idlisseus endpoint:

```text
Endpoint: Codex CLI · Native Skills
Model:    gpt-5.4-codex-native-skills
URL:      http://host.docker.internal:7011/v1
```

Refresh Idlisseus, make a new chat, and select that model. Keep the Idlisseus mode toggle on
**Chat**. Codex CLI is already the agent; selecting Idlisseus Agent mode merely adds an unnecessary
outer loop. It will generally still answer, but it is not the benchmarked architecture.

Codex executes inside the already-running `hermes-live` container as the unprivileged `nobody`
user. The setup does not create, stop, or restart a container. This avoids the host's broken
`bwrap` sandbox while preserving the isolated runner used by the benchmark.

Check or stop only this bridge:

```bash
/home/beeps/src/github.com/bprashanth/idlisseus/chatbots/odysseus/venv/bin/python \
  ecology_memory/integration/codex_native/setup_idlisseus.py status

/home/beeps/src/github.com/bprashanth/idlisseus/chatbots/odysseus/venv/bin/python \
  ecology_memory/integration/codex_native/setup_idlisseus.py stop
```

This does not start, stop, or reconfigure Hermes or any model server.

## Live local audit client

For the structured stream, read the generated bridge token without printing it:

```bash
export CODEX_NATIVE_API_TOKEN="$(cat ecology_memory/integration/codex_native/runs/service/.api-token)"
python3 ecology_memory/integration/codex_native/chat.py --direct
```

The direct client prints events as Codex produces them. It does not pause Codex between internal
commands: the noninteractive Codex CLI has no safe checkpoint/resume protocol for individual tool
calls. It pauses naturally for each next user turn, and the complete event stream is retained.

One question without the REPL:

```bash
python3 ecology_memory/integration/codex_native/chat.py --direct \
  --question 'Is EBTL becoming greener since 2019?'
```

The equivalent structured curl is:

```bash
curl -N http://127.0.0.1:7011/v1/audit/chat \
  -H "Authorization: Bearer $CODEX_NATIVE_API_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"my-ebtl-test","message":"Is EBTL becoming greener since 2019?"}'
```

Reuse the same `session_id` for follow-ups. Every SSE object is an audit event; the final object
contains the answer and the resumable Codex thread id.

## Through the remote Idlisseus API

Create/select a browser chat using the Codex-native model and copy its session id. Generate a
normal Idlisseus API token with `chat` scope in Settings. From a laptop:

```bash
export ODYSSEUS_URL=https://chat.idli.cc
export ODYSSEUS_API_TOKEN=ody_your_scoped_token
export ODYSSEUS_SESSION=the_browser_chat_session_id

python3 ecology_memory/integration/codex_native/chat.py
```

Equivalent one-turn curl (the response is SSE):

```bash
curl -N -X POST "$ODYSSEUS_URL/api/chat_stream" \
  -H "Authorization: Bearer $ODYSSEUS_API_TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "session=$ODYSSEUS_SESSION" \
  --data-urlencode "mode=chat" \
  --data-urlencode "message=Is EBTL becoming greener since 2019?"
```

## Security boundary

The bridge requires a bearer token and exposes only an allowlisted skill gateway. Codex gets a
private home and workspace per session and runs as uid/gid 65534 inside the existing Hermes
container; that user cannot traverse the mounted Hermes data directory. Public web search is not
enabled. The container still has outbound network access and a general shell, and the host bridge
itself can issue narrowly constructed `docker exec` calls. Therefore this is a trusted-team POC,
not a hardened public multi-tenant boundary. Before public use, move the runner into a dedicated
long-lived sandbox with an egress allowlist and no unrelated host mounts.

The frozen manual questions are in
`../../narrative/benchmarks/skills-agent-harness-v2/questions.json`.
