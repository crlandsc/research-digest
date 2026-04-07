# Product Spec

## Working title

research-digest

## One-sentence summary

A local-first tool that fetches recent arXiv papers, filters and ranks them against configured interests, and generates a readable research digest.

## Problem

It is easy to miss relevant papers because:
- arXiv publishes a large volume of new material
- broad categories contain too much noise
- manual review is time-consuming
- the useful signal is often buried across many titles and abstracts

The tool should reduce that overhead and create a repeatable digest workflow.

## Target user

Primary user:
- a single technical researcher, engineer, or builder who wants a curated recurring paper digest

Secondary future users:
- a small team sharing topics and digests

## Core user outcome

The user should be able to run one command and get a digest of the most relevant recent papers for their configured interests.

## MVP scope

Version 1 must support:

1. topic configuration via a local config file
2. fetching recent papers from arXiv
3. normalizing paper metadata locally
4. local persistence of fetched results
5. filtering and ranking papers
6. generating a Markdown digest locally
7. a local CLI for running the workflow

## Acceptable MVP shortcuts

These are acceptable for the first useful version:

- ranking can be heuristic rather than ML-based
- summaries can rely on the arXiv abstract
- an extractive summary is acceptable
- output can be Markdown only
- delivery can be local file output only
- scheduling can be manual at first
- configuration can be file-based only

## Explicit non-goals for MVP

Do **not** make these part of the first critical path unless the docs are updated:

- multi-user auth
- payments
- a hosted web app
- a polished frontend dashboard
- email delivery as a required feature
- Slack/Discord integration as a required feature
- vector databases
- complex agent orchestration
- provider lock-in
- paid APIs as a hard dependency

## Source scope

For v1:
- source = arXiv only

Future possible sources:
- Semantic Scholar
- bioRxiv
- SSRN
- conference feeds

These future sources should not complicate the initial implementation.

## Primary workflow

1. user defines interests in config
2. tool fetches recent papers from arXiv
3. tool stores normalized metadata locally
4. tool filters and ranks candidates
5. tool generates a digest file
6. user reviews digest locally

## Functional requirements

### FR-1 Topic configuration
The system must support a local config file for:
- categories
- keyword queries
- inclusion/exclusion filters
- digest preferences

### FR-2 Fetch recent papers
The system must fetch recent papers from arXiv based on configured categories and/or queries.

### FR-3 Normalize metadata
The system must normalize at least:
- arXiv ID
- title
- authors
- abstract/summary
- categories
- published date
- updated date if available
- source URL
- PDF URL if available

### FR-4 Local persistence
The system must persist fetched metadata locally so the digest pipeline is resumable and deduplication is possible.

### FR-5 Ranking
The system must rank or score candidate papers using deterministic logic first. LLM-based enhancement is optional later.

### FR-6 Digest output
The system must produce a readable Markdown digest including at least:
- title
- link
- short excerpt or summary
- why it was selected or score rationale

### FR-7 CLI
The system must expose a CLI suitable for local use.

## Quality requirements

- simple local setup
- low operational complexity
- readable code structure
- resumable state
- test coverage for core pipeline pieces
- minimal human setup before first useful result

## Definition of done for first useful release

The first useful release is done when a user can:

1. configure topics locally
2. run the CLI locally
3. fetch recent arXiv papers
4. store and deduplicate them locally
5. generate a Markdown digest with sensible ranking
6. inspect the digest in the local filesystem

## Deferred features

These can come later:

- LLM-generated summaries
- scheduled runs
- delivery by email
- team sharing
- hosted deployment
- admin UI
- feedback loops
- saved relevance tuning