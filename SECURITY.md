# Security & API-key handling

MMR runs on a **bring-your-own-key (BYOK)** model: each user supplies their own
Google Gemini and AssemblyAI API keys, and the analysis runs on those keys. This
document explains exactly what happens to a key so you can decide whether to trust
a given deployment.

## What happens to your API keys

1. **In your browser** the key is typed into a password field. It is kept only in
   page memory — it is **never** written to `localStorage`, cookies, or any other
   browser storage. Refreshing the page discards it.
2. **It is sent once**, over the network, with your analysis request.
3. **The server never stores it.** There is no API-key column on the job record, no
   database row, and no file that holds it. It exists only as an in-memory value for
   the duration of your one job, then is discarded when the job finishes.
4. **It is never logged.** Application logs record HTTP status codes, not key values.
   As a safeguard, if a job fails, any key string is redacted from the saved
   traceback before it is written to the job log.
5. **It is used only to call the official providers** — Google's Generative Language
   API and AssemblyAI — and nowhere else. The Gemini key is sent in an
   `x-goog-api-key` request header, never in a URL/query string.

Concretely: your video, your report, and the logs contain **zero** key material.

## The honest limitation

For any server that *processes* your key, the key must be held in plaintext for a
moment in order to call the provider. So while this codebase does not store, log, or
transmit your key anywhere except the provider, **you are ultimately trusting the
operator of the deployment you use** — a malicious or compromised operator could, in
principle, modify the code to capture it. This is inherent to BYOK on a server; there
is no cryptographic guarantee that removes it.

What makes that trust reasonable:

- **The code is open and inspectable** — the data flow above is the whole story.
- **HTTPS is required in production.** Without TLS the key is exposed in transit.
  Only use a deployment served over `https://`.
- **You stay in control of the key** (see below).

## Recommendations for users

- **Use a restricted or throwaway key.** Scope a Gemini key to the Generative
  Language API; set low quotas where possible. If it ever leaks, the blast radius is
  small.
- **Revoke when you're done.** Both Google AI Studio and the AssemblyAI dashboard let
  you rotate or delete a key in one click.
- **Watch your usage.** Both providers show request counts, so you can confirm the key
  was used only for your run.
- **Only enter keys on an `https://` deployment** you trust.

## Recommendations for operators

- Serve only over **HTTPS** (terminate TLS at a reverse proxy / platform).
- Restrict `CORS_ORIGINS` to your real domain and set `MMR_TEST_MODE=0`.
- Do not add logging that echoes request form fields.
- Keep the BYOK promise: never persist user keys to the database, disk, or logs.

## Reporting a vulnerability

If you find a security issue, please report it privately to the repository owner
rather than opening a public issue.
