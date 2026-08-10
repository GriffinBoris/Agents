# Plain Technical Writing

Use these rules for technical documentation, READMEs, pull-request descriptions, release notes, comments, tool descriptions, system prompts, and agent messages.

## Terms and Words

- Use one term for one concept. Do not rotate among near-synonyms when readers could infer different meanings.
- Use a word with one meaning in the same artifact when a second meaning could create ambiguity.
- Prefer short, familiar words when they preserve the technical meaning.
- Use concrete nouns and direct verbs. Replace nominalizations such as "perform an analysis" with the action itself, such as "analyze."
- Remove filler, vague transitions, empty conclusions, and unsupported promotional adjectives.
- Keep necessary domain vocabulary. Plain language must not make a precise term less accurate.

## Verbs and Sentences

- Prefer active voice when the actor matters or is known. Use passive voice when the actor is unknown, irrelevant, or intentionally omitted.
- Do not mistake a past participle used as an adjective, such as "the field is required," for passive voice.
- Use simple verb forms when they express the same timing and meaning. Remove stacked helper verbs and hedging that do not carry a real qualification.
- Replace a phrasal verb with a precise verb when the replacement is clearer. Keep established technical terms when changing them would reduce clarity.
- Give each instruction one primary action. If two actions are independent, use separate sentences or steps.
- Put a condition before the action it controls: "If the test fails, read the log."
- Keep sentences focused, but do not delete facts or qualifiers merely to shorten them.

## Structure

- Keep each paragraph focused on one topic.
- Connect related sentences with plain transitions instead of leaving a string of disconnected statements.
- Use a numbered vertical list for an ordered procedure. Start each step with an imperative verb.
- A label, changelog item, or compact status line does not need to become a full sentence.
- Define an abbreviation on first use unless the audience and repository already treat it as standard.
- Unpack long noun clusters when their relationships are hard to parse.

## Rewrite Guards

- Preserve every fact, number, condition, scope qualifier, and relationship.
- Preserve code identifiers, command syntax, paths, part numbers, units, error strings, quotations, and required safety or legal wording exactly.
- Change the smallest span that fixes the issue. Do not restyle compliant text without a reason.
- Do not replace a qualified word such as "can," "may," "should," or "must" unless the replacement preserves permission, possibility, recommendation, and obligation exactly.
- Do not add an introduction, recap, or closing that the artifact does not need.

## Review Checklist

1. Does one concept have multiple names?
2. Can a direct verb replace a nominalization or vague verb phrase?
3. Does passive voice hide an actor the reader needs to know?
4. Does any sentence combine independent instructions or unnecessary clauses?
5. Does each paragraph have one topic and a clear purpose?
6. Did the edit preserve every fact, qualifier, and technical literal?

This guidance adapts the MIT-licensed [ste-writing skill](https://github.com/woosal1337/blog/blob/main/videos/ep01-the-cure-for-ai-slop/ste-writing-skill.md), which draws from ASD-STE100 Issue 9. It is an unofficial plain-language aid, not a certified STE checker.
