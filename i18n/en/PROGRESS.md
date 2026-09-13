# EN translation progress (i18n/en/)

Owner: translation agent. Files here are the only outputs of this agent. All steps complete.

## Done
- notes.json: all 90 stories translated; keys, order and paragraph counts identical to RU; URLs and digits verified identical per story.
- artists.json: 82 tokens mapped (tiles + ALBUMS + feats.json), 12 kept Cyrillic per Spotify; notes in `_notes` / `_romanization`.
- templates.json: 62 named patterns (track page, hub, index footer/alts, JSON-LD bylines, redirect stub, FAQ counter phrase) + `roles` (ROLE_WORD, ROLE_VERB, ROLE_NAME_LD, ROLE_ALT, MIXED_ALT) + plural rules.
- ui.json: 137 entries for index.html and faq/index.html (all 32 Q + 32 answer paragraphs with inline HTML verbatim). Counter elements collapse to {tracks}/{artists} in keys; EN values re-emit them as <span data-n="works|artists"> so patch_faq-style regexes can fill EN pages. `_contact_by_href` resolves the contradictory Telegram labels by href.
- llms.txt: EN version with {tracks}/{artists} placeholders, RU URLs kept, no invented facts.
- humanizer pass applied to notes.json, ui.json, llms.txt (templates.json needed no changes); invariants (URLs, digits, placeholders, tags) asserted unchanged; all JSON re-parsed.

## Open items for the owner / other agents
- Telegram name-to-handle mapping contradicts between index.html and faq/index.html; EN uses neutral handle labels (`_contact_by_href`).
- pizza-zoloto and pizza-navai-grustnyy-ekonom: roles.json says mix, the story says mixing and mastering; translated faithfully, not resolved.
- Curly quotes “…” are used for release titles in EN (RU uses «…»); a deliberate typographic choice for the credits page.
