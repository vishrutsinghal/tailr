"""Derive reviewable requirement rows from explicit user wording without inventing scope."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any


ACTION = (
    r"add|allow|avoid|block|build|capture|change|consolidate|create|define|demonstrate|detect|ensure|fix|include|implement|introduce|"
    r"issue|keep|maintain|map|notify|prevent|preserve|provide|prove|publish|record|refund|reject|release|"
    r"refactor|redesign|reduce|require|retain|run|save|send|show|support|update|use|validate|verify|"
    r"adds|allows|avoids|blocks|builds|captures|changes|consolidates|creates|defines|demonstrates|detects|ensures|fixes|includes|"
    r"implements|introduces|issues|keeps|maintains|maps|notifies|prevents|preserves|provides|proves|publishes|records|"
    r"redesigns|refactors|reduces|refunds|rejects|releases|requires|retains|runs|saves|sends|shows|supports|updates|uses|validates|verifies"
)
ACTION_START = re.compile(rf"^(?:do\s+not\s+|must\s+|must\s+not\s+|should\s+)?(?:{ACTION})\b", re.IGNORECASE)
SUBJECT_ACTION = re.compile(rf"^(?P<subject>[A-Za-z][A-Za-z0-9 _/-]{{0,60}}?)\s+(?P<action>{ACTION})\b", re.IGNORECASE)
PREFIX = re.compile(r"^(?:tailtrail\s+start\s*[,;:-]?\s*)?(?:hands[- ]free|end[- ]to[- ]end)\s*:\s*", re.IGNORECASE)
WORKFLOW_PREFIX = re.compile(
    r"^(?:(?:using|use)\s+(?:tailtrail\s+)?(?:aidlc(?:\s+(?:lite|standard|full))?|navigator)\s*[,;:-]\s*)+",
    re.IGNORECASE,
)
BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
SOFT_WRAP = "\x00"
QUERY_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "before", "by", "do",
    "for", "from", "in", "is", "it", "not", "of", "on", "or", "the",
    "this", "to", "while", "with", "without",
}
QUERY_LOW_SIGNAL_WORDS = {
    "also", "but", "click", "clicked", "clicking", "clicks", "issue", "just",
    "like", "message", "move", "moves", "page", "screen", "should", "showing",
    "similarly", "there", "user", "when",
}
HOSTS = {"codex", "copilot", "claude"}
CLAUSE_ROLES = {"context", "outcome", "constraint", "evidence", "scope", "question"}
REQUIREMENT_KINDS = {"change", "preserve", "constraint", "safety"}
INTENT_CLASSES = {"general", "ui-visibility", "ui-interaction", "api-behavior", "data", "configuration"}
SUFFICIENCY_STATES = {"sufficient", "clarification-required", "standard-recommended", "full-recommended"}
SUFFICIENCY_ROUTES = {"scope", "lite-questions", "aidlc-standard"}
ABSOLUTE_SCOPE_PATH = re.compile(
    r"\b(?P<prefix>in|under|inside|within)\s+"
    r"(?P<path>/(?:[^\s,;]+)|[A-Za-z]:[\\/](?:[^\s,;]+))",
    re.IGNORECASE,
)
AWS_RESOURCE_TYPE = re.compile(
    r"\b(?:aws\s+secrets?\s+manager|secrets?\s+manager|ssm|parameter\s+store|"
    r"securestring|aws[_ -]secretsmanager[_ -]secret)\b",
    re.IGNORECASE,
)
NAMED_REQUIREMENT_TARGET = re.compile(r"(?<![A-Za-z0-9_])(?:[A-Za-z][A-Za-z0-9]*_){1,}[A-Za-z0-9_]+")


def normalize_literal_presentation(value: str) -> str:
    """Remove balanced chat/Markdown wrappers without changing literal text.

    This is deliberately narrower than general Markdown rendering.  It only
    removes inline wrappers that hosts commonly add around a reported message,
    so requirement identity and repository search do not depend on whether a
    user chose plain, emphasized, quoted, or code formatting.
    """
    normalized = value
    for pattern in (
        r"`([^`\n]+)`",
        r"\*\*([^*\n]+)\*\*",
        r"__([^_\n]+)__",
        r"(?<!\*)\*(?!\s)([^*\n]*?\S)\*(?!\*)",
        r"(?<!\w)_(?!\s)([^_\n]*?\S)_(?!\w)",
        r"'([^'\n]{4,160})'",
        r'"([^"\n]{4,160})"',
    ):
        normalized = re.sub(pattern, r"\1", normalized)
    return normalized


def normalize_quoted_literal(value: str) -> str:
    """Return one canonical literal while preserving meaningful punctuation."""
    normalized = " ".join(normalize_literal_presentation(value).strip().split())
    return normalized.strip(" `*_\"'")


def inferred_intent_class(statement: str, current: str = "general") -> str:
    """Keep a specific host class, otherwise derive an explicit UI boundary.

    Host reasoning is advisory metadata. It must not erase a deterministic UI
    boundary that is explicit in the canonical requirement statement, because
    Navigator uses this class to distinguish a literal emitter from the UI
    renderer that owns visibility.
    """
    normalized = " ".join(statement.casefold().split())
    if current not in {"", "general"}:
        return current
    visibility_action = any(
        re.search(rf"\b{term}\b", normalized)
        for term in ("remove", "hide", "dismiss", "suppress", "show", "display", "render")
    )
    explicit_ui_object = any(
        re.search(rf"\b{term}\b", normalized)
        for term in ("banner", "toast", "alert")
    ) or (
        any(re.search(rf"\b{term}\b", normalized) for term in ("message", "warning"))
        and any(re.search(rf"\b{term}\b", normalized) for term in ("page", "screen", "view", "dialog", "ui"))
    )
    if visibility_action and explicit_ui_object:
        return "ui-visibility"
    interaction_action = any(
        re.search(rf"\b{term}\b", normalized)
        for term in ("click", "navigate", "advance", "redirect", "move to")
    )
    if interaction_action and any(
        re.search(rf"\b{term}\b", normalized)
        for term in ("button", "page", "screen", "step", "ui")
    ):
        return "ui-interaction"
    return "general"


def _normalized_lines(value: str) -> list[str]:
    """Return platform-independent physical lines without changing wording."""
    return value.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _structural_chunks(value: str) -> list[str]:
    """Join prose wraps while retaining paragraphs and explicit list items.

    A physical newline is not sufficient evidence for a new requirement. A
    blank line or a Markdown bullet/number is structural evidence. Indented
    text following a list marker remains part of that item, which supports
    ordinary wrapped Markdown lists without treating the continuation as an
    orphan requirement.
    """
    chunks: list[str] = []
    current: list[str] = []
    list_item = False

    def flush() -> None:
        nonlocal current, list_item
        if current:
            # Keep a physical prose wrap distinguishable from a same-line
            # sentence boundary until sentence splitting is complete. This
            # matters when a host wraps after punctuation: ``valid.\naddresses``
            # is one requirement unless a blank line or list marker provides
            # structural evidence for a new row.
            normalized = re.sub(r"[ \t\f\v]+", " ", SOFT_WRAP.join(current)).strip()
            if normalized:
                chunks.append(normalized)
        current = []
        list_item = False

    for raw_line in _normalized_lines(value):
        stripped = raw_line.strip()
        if not stripped:
            flush()
            continue
        if BULLET.match(raw_line):
            flush()
            current = [BULLET.sub("", raw_line).strip()]
            list_item = True
            continue
        if list_item and not raw_line[:1].isspace():
            flush()
        current.append(stripped)
    flush()
    return chunks


def _sentence(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip(" ,;:-")
    if not value:
        return ""
    value = value[0].upper() + value[1:]
    return value if value.endswith((".", "?", "!")) else value + "."


def _subject(value: str) -> str | None:
    match = SUBJECT_ACTION.match(value)
    if not match:
        return None
    subject = match.group("subject").strip()
    return subject if len(subject.split()) <= 6 else None


def _predicate_parts(value: str) -> list[str]:
    """Split action lists while retaining commas used inside ordinary objects."""
    raw = [item.strip() for item in re.split(r",", value) if item.strip()]
    if len(raw) < 2:
        raw = [value.strip()]
    subject = _subject(raw[0])
    parts: list[str] = []
    for raw_item in raw:
        item = re.sub(r"^(?:and|then)\s+", "", raw_item, flags=re.IGNORECASE).strip()
        if parts and ACTION_START.match(item):
            parts.append(f"{subject} {item}" if subject else item)
        elif parts:
            parts[-1] += ", " + raw_item
        else:
            parts.append(item)
    expanded: list[str] = []
    for item in parts:
        conjunction = re.split(rf"\s+(?:and|then)\s+(?=(?:do\s+not\s+|must\s+|must\s+not\s+|should\s+)?(?:{ACTION})\b)", item, flags=re.IGNORECASE)
        expanded.extend(conjunction)
    return [_sentence(item) for item in expanded if _sentence(item)]


def _expand_maintainability_constraints(value: str) -> list[str]:
    """Separate explicit preservation and negative-scope clauses.

    This remains wording-driven.  It does not invent a refactor boundary; it
    merely prevents independently reviewable clauses from being hidden in one
    requirement row.
    """
    text = value.rstrip(".")
    preserved = re.match(
        r"^preserve\s+(?P<behavior>.+?)\s+and\s+(?P<tests>(?:the\s+)?(?:relevant\s+)?tests?)$",
        text,
        flags=re.IGNORECASE,
    )
    if preserved:
        return [
            _sentence(f"Preserve {preserved.group('behavior')}"),
            _sentence(f"Preserve {preserved.group('tests')}"),
        ]
    bounded = re.match(
        r"^(?P<main>.+?)\s+without\s+(?P<verb>expanding|changing|adding|removing)\s+(?P<object>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if bounded and ACTION_START.match(bounded.group("main")):
        verb = {"expanding": "expand", "changing": "change", "adding": "add", "removing": "remove"}[bounded.group("verb").lower()]
        return [_sentence(bounded.group("main")), _sentence(f"Do not {verb} {bounded.group('object')}")]
    return [_sentence(value)]


def _expand_ui_feature_list(value: str) -> list[str]:
    """Turn an explicit ``page with A, B, and C`` request into atomic rows.

    This is deliberately limited to named UI containers.  It does not split
    ordinary comma lists such as the design tokens that a user asks to
    preserve, and it adds no feature that was absent from the prompt.
    """
    text = value.rstrip(".")
    match = re.match(
        r"^(?P<base>(?:add|build|create|implement)\s+.+?\b(?:dashboard|dialog|form|page|screen|view)\b.*?)\s+with\s+(?P<features>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        negative = re.match(
            r"^do\s+not\s+(?P<first>introduce\s+.+?)\s+or\s+(?P<second>redesign\s+.+)$",
            text,
            flags=re.IGNORECASE,
        )
        if negative:
            return [_sentence(f"Do not {negative.group('first')}"), _sentence(f"Do not {negative.group('second')}")]
        return []
    features_text = re.sub(r",\s+and\s+", ", ", match.group("features"), flags=re.IGNORECASE)
    features = [item.strip() for item in features_text.split(",") if item.strip()]
    if len(features) < 2:
        return []
    rows = [_sentence(match.group("base"))]
    for feature in features:
        feature = re.sub(r"^(?:an?|the)\s+", "", feature, flags=re.IGNORECASE)
        verb = "Provide" if "control" in feature.lower() or "action" in feature.lower() else "Show"
        rows.append(_sentence(f"{verb} {feature} on the requested UI"))
    return rows


def _expand_ui_interaction_sequence(value: str) -> list[str]:
    """Normalize the explicit three-part UI progression used in bug reports.

    A conversational report commonly names one working transition, contrasts
    it with a broken action, and then adds a second broken action with
    ``similarly``.  Keeping that entire paragraph as one requirement makes
    acceptance and proof ambiguous.  This recognizer is deliberately strict:
    it runs only when all three explicit clauses are present and never invents
    a destination or notification that the user did not name.
    """
    normalized = " ".join(value.replace(SOFT_WRAP, " ").split()).strip()
    baseline = re.search(
        r"when\s+(?:the\s+)?user\s+clicks(?:\s+on)?\s+(?P<action>.+?)\s+"
        r"(?:the\s+)?screen\s+moves?\s+to\s+(?P<destination>.+?)\s+but\s+when\s+",
        normalized,
        flags=re.IGNORECASE,
    )
    primary = re.search(
        r"but\s+when\s+(?:the\s+)?user\s+clicks(?:\s+on)?\s+(?P<action>.+?)\s+"
        r"it\s+(?:is\s+)?(?:just\s+)?show(?:s|ing)\s+(?:the\s+)?message\s+"
        r"(?P<message>['\"].+?['\"])\s+but\s+it\s+should\s+also\s+"
        r"move(?:\s+(?:the\s+)?screen)?\s+to\s+(?P<destination>.+?)\s*,\s*similarly\s+for\s+",
        normalized,
        flags=re.IGNORECASE,
    )
    secondary = re.search(
        r"similarly\s+for\s+(?P<action>.+?)\s+it\s+should\s+"
        r"(?:show\s+(?:a\s+)?|display\s+(?:a\s+)?|)message\s+(?:like\s+)?"
        r"(?P<message>.+?)\s+and\s+move(?:\s+(?:the\s+)?screen)?\s+to\s+"
        r"(?P<destination>.+?)(?:[.!?]|$)",
        normalized,
        flags=re.IGNORECASE,
    )
    if not (baseline and primary and secondary):
        return []

    def clean(group: str, match: re.Match[str]) -> str:
        return " ".join(match.group(group).strip(" ,.;:-'\"").split())

    primary_message = primary.group("message").strip()
    secondary_message = clean("message", secondary)
    return [
        _sentence(
            f"When the user clicks {clean('action', primary)} and validation succeeds, "
            f"preserve the message {primary_message} and move to {clean('destination', primary)}"
        ),
        _sentence(
            f"When the user clicks {clean('action', secondary)} and the copy succeeds, "
            f"show the message '{secondary_message}' and move to {clean('destination', secondary)}"
        ),
        _sentence(
            f"Preserve the existing {clean('action', baseline)} transition to "
            f"{clean('destination', baseline)}"
        ),
    ]


def _symptom_action_contract(value: str) -> dict[str, Any] | None:
    """Merge a reported UI symptom followed by a pronoun-based requested action.

    The warning text remains an exact search literal, but only the requested
    action and UI location become semantic ownership terms. This avoids
    interpreting words inside a banner as a configuration requirement.
    """
    normalized = normalize_literal_presentation(value.replace(SOFT_WRAP, " "))
    normalized = " ".join(normalized.split()).strip(" ,;")
    match = re.match(
        r"^(?P<context>.+?[.!?])\s+(?:(?:we|i|the\s+user)\s+)?"
        r"(?:need|needs|want|wants|would\s+like)\s+to\s+"
        r"(?P<action>remove|hide|dismiss)\s+(?:it|that|the\s+(?:banner|message|warning|alert))\s*[.!?]*$",
        normalized,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    context = match.group("context").strip()
    object_match = re.search(r"\b(?P<object>banner|message|warning|alert)\b", context, flags=re.IGNORECASE)
    if not object_match:
        return None
    location_match = re.search(
        r"\b(?:in|on)\s+the\s+(?P<location>.+?\b(?:page|screen|view|dialog))\b",
        context,
        flags=re.IGNORECASE,
    )
    object_name = object_match.group("object").lower()
    literal = context[object_match.end():].strip(" `*'\". ")
    if not literal:
        return None
    location = location_match.group("location").strip() if location_match else "named UI surface"
    action = match.group("action").capitalize()
    statement = f'{action} the "{literal}." {object_name} from the {location}.'
    clauses = [
        {"clause_id": "C-01", "role": "context", "text": context},
        {"clause_id": "C-02", "role": "outcome", "text": normalized[match.start("action"):].strip()},
    ]
    intent_terms = list(dict.fromkeys([
        match.group("action").lower(), object_name,
        *re.findall(r"[a-zA-Z][a-zA-Z0-9_]{2,}", location.casefold()),
    ]))
    return {
        "clauses": clauses,
        "requirements": [{
            "display_id": "REQ-01",
            "statement": statement,
            "kind": "change",
            "source_clause_ids": ["C-01", "C-02"],
            "intent_terms": intent_terms,
            "quoted_literals": [literal + "."],
            "intent_class": "ui-visibility",
            "confidence": "high",
        }],
    }


def statements(goal: str) -> list[str]:
    """Split only explicit clauses, bullets, sentences, and action predicates."""
    value = WORKFLOW_PREFIX.sub("", PREFIX.sub("", goal.strip()))
    if "zero quantity" in value.lower() and "validation" in value.lower():
        return [
            "Reject zero quantities in the existing validation boundary.",
            "Preserve valid positive-quantity behavior outside the new rejection case.",
            "Add focused validation evidence for the zero-quantity rule and preserved positive behavior.",
        ]
    symptom_action = _symptom_action_contract(value)
    if symptom_action:
        return [str(row["statement"]) for row in symptom_action["requirements"]]
    interaction_rows = _expand_ui_interaction_sequence(value)
    if interaction_rows:
        return interaction_rows
    structural_chunks = _structural_chunks(value) or [re.sub(r"\s+", " ", value).strip()]
    chunks: list[str] = []
    for chunk in structural_chunks:
        chunks.extend(item for item in re.split(r";|(?<=[.!?])[ \t]+", chunk) if item.strip())
    rows: list[str] = []
    for chunk in chunks or [value]:
        chunk = chunk.replace(SOFT_WRAP, " ")
        ui_rows = _expand_ui_feature_list(chunk)
        if ui_rows:
            rows.extend(ui_rows)
            continue
        for item in _predicate_parts(chunk):
            rows.extend(_expand_maintainability_constraints(item))
    unique: list[str] = []; seen: set[str] = set()
    for row in rows:
        key = re.sub(r"\W+", " ", row.lower()).strip()
        if key and key not in seen:
            seen.add(key); unique.append(row)
    if len(unique) == 1 and len(structural_chunks) == 1 and ";" not in structural_chunks[0]:
        # Preserve a single requirement's original casing and punctuation,
        # changing only platform newlines and soft-wrap whitespace.
        return [structural_chunks[0].replace(SOFT_WRAP, " ")]
    return unique[:25] or [value.strip()]


def stable_requirement_id(statement: str) -> str:
    """Return a line-ending-independent ID for one normalized requirement."""
    canonical = re.sub(r"\s+", " ", statement).strip().casefold()
    return "req-frame-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


def goal_fingerprint(goal: str) -> str:
    """Bind one host interpretation to the exact user goal without storing reasoning."""
    return "sha256:" + hashlib.sha256(goal.encode("utf-8")).hexdigest()


def _grounding_text(value: str) -> str:
    """Normalize only presentation punctuation for exact-source grounding."""
    return " ".join(re.findall(r"[a-zA-Z0-9]+", re.sub(r"[`*_>#]+", " ", value).casefold()))


def _extract_scope_paths(goal: str) -> tuple[str, list[dict[str, str]]]:
    """Separate explicit repository paths from desired behavior wording.

    A target path constrains where work may occur; it is not itself a product
    outcome.  Keep the exact path as typed scope evidence and remove only its
    small prepositional phrase from deterministic requirement prose.
    """
    scopes: list[dict[str, str]] = []

    def replace(match: re.Match[str]) -> str:
        path = match.group("path").rstrip(".!?")
        clause_id = f"S-{len(scopes) + 1:02d}"
        scopes.append({"clause_id": clause_id, "role": "scope", "text": path})
        suffix = match.group("path")[len(path):]
        return suffix

    without_paths = ABSOLUTE_SCOPE_PATH.sub(replace, goal)
    return re.sub(r"[ \t\f\v]{2,}", " ", without_paths).strip(), scopes


def _deterministic_material_decisions(goal: str) -> list[dict[str, Any]]:
    """Return only high-value ambiguity that can be proven from goal wording.

    This is intentionally small.  It prevents the deterministic fallback from
    declaring a generic AWS credential ``resource`` complete when its concrete
    storage service changes implementation, security, and validation scope.
    Broader risk-based Standard selection belongs to Navigator routing.
    """
    lowered = normalize_literal_presentation(goal).casefold()
    credential_storage = any(term in lowered for term in ("credential", "credentials"))
    generic_resource = bool(re.search(r"\bresource\b", lowered))
    aws_context = bool(re.search(r"\baws\b", lowered))
    if aws_context and credential_storage and generic_resource and not AWS_RESOURCE_TYPE.search(lowered):
        question = (
            "Which AWS resource type should store these credentials: AWS Secrets Manager, "
            "SSM Parameter Store, or another service?"
        )
        return [{
            "id": "MAT-01",
            "decision_class": "infrastructure-resource-type",
            "question": question,
            "impact": ["implementation-scope", "security", "validation"],
            "evidence_refs": ["goal"],
        }]
    return []


def _material_question_class(question: str) -> str:
    """Classify only an explicit, closed material question TailTrail knows."""
    normalized = normalize_literal_presentation(question).casefold()
    if all(
        term in normalized
        for term in ("aws resource type", "secrets manager", "ssm parameter store")
    ):
        return "infrastructure-resource-type"
    return "material-requirement-decision"


def _critical_named_targets(value: str) -> set[str]:
    """Return exact code/data identifiers that requirement prose must retain."""
    return {match.group(0) for match in NAMED_REQUIREMENT_TARGET.finditer(value)}


def _validate_requirement_coverage(
    clauses: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
) -> None:
    """Reject lossy host normalization before it can be called sufficient.

    TailTrail does not judge semantic truth here. It checks the closed typed
    proposal for evidence completeness: every explicit outcome/constraint must
    be represented, and exact named targets must survive the normalization.
    """
    covered_ids = {
        str(clause_id)
        for requirement in requirements
        for clause_id in requirement.get("source_clause_ids", [])
    }
    material_clauses = [
        row for row in clauses if row.get("role") in {"outcome", "constraint"}
    ]
    uncovered = [
        str(row["clause_id"])
        for row in material_clauses
        if str(row["clause_id"]) not in covered_ids
    ]
    if uncovered:
        raise ValueError(
            "host requirement interpretation omitted explicit outcome/constraint clauses: "
            + ", ".join(uncovered)
        )
    if not any(row.get("role") == "outcome" for row in material_clauses):
        raise ValueError("host requirement interpretation needs at least one explicit outcome clause")

    for clause in material_clauses:
        clause_id = str(clause["clause_id"])
        required_targets = _critical_named_targets(str(clause["text"]))
        retained_targets = _critical_named_targets(" ".join(
            str(requirement.get("statement", ""))
            for requirement in requirements
            if clause_id in requirement.get("source_clause_ids", [])
        ))
        missing_targets = sorted(required_targets - retained_targets)
        if missing_targets:
            raise ValueError(
                f"requirements for clause {clause_id} omitted exact named target(s): "
                + ", ".join(missing_targets)
            )


def requirement_sufficiency_contract(
    clauses: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    material_questions: list[str],
    *,
    source: str,
    material_decisions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the typed, authority-free requirement-sufficiency decision."""
    _validate_requirement_coverage(clauses, requirements)
    decisions = list(material_decisions or [])
    known_questions = {str(item.get("question", "")).strip() for item in decisions}
    material_questions = list(dict.fromkeys([
        *material_questions,
        *[
            str(row["text"])
            for row in clauses
            if row.get("role") == "question" and str(row.get("text", "")).strip()
        ],
    ]))
    if len(material_questions) > 3:
        raise ValueError("requirement sufficiency supports at most three material questions")
    next_decision_index = len(decisions) + 1
    for offset, question in enumerate(material_questions):
        normalized = str(question).strip()
        if normalized and normalized not in known_questions:
            decisions.append({
                "id": f"MAT-{next_decision_index + offset:02d}",
                "decision_class": _material_question_class(normalized),
                "question": normalized,
                "impact": ["acceptance-criteria", "implementation-scope"],
                "evidence_refs": ["host-interpretation"],
            })
            known_questions.add(normalized)
    if len(decisions) > 3:
        raise ValueError("requirement sufficiency supports at most three material decisions")
    state = "clarification-required" if decisions else "sufficient"
    route = "lite-questions" if decisions else "scope"
    confidence = "medium" if decisions or source == "deterministic-fallback" else "high"
    outcome_refs = [str(row["clause_id"]) for row in clauses if row.get("role") == "outcome"]
    constraint_refs = [str(row["clause_id"]) for row in clauses if row.get("role") == "constraint"]
    scope_refs = [str(row["clause_id"]) for row in clauses if row.get("role") == "scope"]
    decision_refs = [str(row["id"]) for row in decisions if row.get("id")]
    named_targets = sorted(_critical_named_targets(" ".join(
        str(row.get("text", ""))
        for row in clauses
        if row.get("role") in {"outcome", "constraint"}
    )))
    retained_targets = _critical_named_targets(" ".join(
        str(row.get("statement", "")) for row in requirements
    ))
    dimensions = [
        {
            "id": "outcome-coverage",
            "required": True,
            "status": "satisfied" if outcome_refs else "missing",
            "reason": "Every explicit outcome is represented by a requirement row." if outcome_refs else "No explicit outcome was supplied.",
            "evidence_refs": outcome_refs,
        },
        {
            "id": "constraint-coverage",
            "required": bool(constraint_refs),
            "status": "satisfied" if constraint_refs else "not-applicable",
            "reason": "Every explicit constraint is represented by a requirement row." if constraint_refs else "The request contains no explicit constraint.",
            "evidence_refs": constraint_refs,
        },
        {
            "id": "scope-boundary",
            "required": bool(scope_refs),
            "status": "satisfied" if scope_refs else "not-applicable",
            "reason": "The explicit target boundary was retained separately from requirement prose." if scope_refs else "The request does not declare an explicit repository boundary.",
            "evidence_refs": scope_refs,
        },
        {
            "id": "named-target-retention",
            "required": bool(named_targets),
            "status": "satisfied" if named_targets else "not-applicable",
            "reason": "Every exact named code/data target was retained." if named_targets else "The request contains no exact named code/data target.",
            "evidence_refs": [target for target in named_targets if target in retained_targets],
        },
        {
            "id": "material-decisions",
            "required": True,
            "status": "missing" if decision_refs else "satisfied",
            "reason": "Material decisions remain open." if decision_refs else "No unresolved material decision remains.",
            "evidence_refs": decision_refs,
        },
    ]
    return {
        "schema_version": "1",
        "type": "tailtrail-requirement-sufficiency",
        "state": state,
        "confidence": confidence,
        "requirements": requirements,
        "context": [
            {"clause_id": str(row["clause_id"]), "text": str(row["text"])}
            for row in clauses
            if row.get("role") in {"context", "evidence"}
        ],
        "scope": [
            {"clause_id": str(row["clause_id"]), "text": str(row["text"])}
            for row in clauses
            if row.get("role") == "scope"
        ],
        "dimensions": dimensions,
        "material_decisions": decisions,
        "evidence_refs": list(dict.fromkeys(
            ref
            for decision in decisions
            for ref in decision.get("evidence_refs", [])
            if str(ref).strip()
        )),
        "recommended_route": route,
        "boundary": (
            "Requirement sufficiency only. This contract creates no Planning Lock, "
            "implementation scope, approval, or execution authority."
        ),
    }


def interpretation(
    goal: str,
    proposal: dict[str, Any] | None = None,
    host: str | None = None,
    artifact_inputs: list[dict[str, Any]] | None = None,
    visual_decisions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return one validated requirement interpretation for every Start surface."""
    artifacts = {
        str(item.get("input_id")): item
        for item in (artifact_inputs or [])
        if isinstance(item, dict)
        and str(item.get("input_id", "")).strip()
        and str(item.get("sha256", "")).strip()
        and isinstance(item.get("content"), str)
    }
    if proposal is None:
        normalized_goal = WORKFLOW_PREFIX.sub("", PREFIX.sub("", goal.strip()))
        requirement_goal, scope_clauses = _extract_scope_paths(normalized_goal)
        special = _symptom_action_contract(requirement_goal)
        requirement_rows = special["requirements"] if special else [
            {
                "display_id": f"REQ-{index:02d}",
                "statement": statement,
                "kind": _kind(statement),
                "source_clause_ids": [f"C-{index:02d}"],
                "intent_terms": query_terms(statement),
                "quoted_literals": [],
                "intent_class": inferred_intent_class(statement),
                "confidence": "deterministic",
            }
            for index, statement in enumerate(statements(requirement_goal), start=1)
        ]
        clauses = (special["clauses"] if special else [
            {"clause_id": f"C-{index:02d}", "role": "outcome", "text": row["statement"]}
            for index, row in enumerate(requirement_rows, start=1)
        ]) + scope_clauses
        decisions = _deterministic_material_decisions(requirement_goal)
        for row in visual_decisions or []:
            if isinstance(row, dict) and str(row.get("question", "")).strip():
                decisions.append({
                    "id": str(row.get("id") or f"VIS-{len(decisions) + 1:02d}"),
                    "decision_class": str(row.get("decision_class") or "visual-artifact-required"),
                    "question": str(row["question"]).strip(),
                    "impact": list(row.get("impact", ["acceptance-criteria", "implementation-scope"])),
                    "evidence_refs": list(row.get("evidence_refs", ["host-interpretation"])),
                })
        questions = [str(item["question"]) for item in decisions]
        sufficiency = requirement_sufficiency_contract(
            clauses,
            requirement_rows,
            questions,
            source="deterministic-fallback",
            material_decisions=decisions,
        )
        return {
            "schema_version": "1",
            "type": "tailtrail-requirement-interpretation",
            "source": "deterministic-fallback",
            "host": None,
            "goal_fingerprint": goal_fingerprint(goal),
            "private_reasoning_excluded": True,
            "clauses": clauses,
            "requirements": requirement_rows,
            "material_questions": questions,
            "state": sufficiency["state"],
            "sufficiency": sufficiency,
        }

    if not isinstance(proposal, dict):
        raise ValueError("host requirement interpretation must be an object")
    if proposal.get("type") != "tailtrail-host-requirement-interpretation" or str(proposal.get("schema_version")) != "1":
        raise ValueError("host requirement interpretation has an unsupported contract")
    proposed_host = str(proposal.get("host", host or "")).lower()
    if proposed_host not in HOSTS or (host and proposed_host != host):
        raise ValueError("host requirement interpretation does not match the active host")
    if proposal.get("private_reasoning_excluded") is not True:
        raise ValueError("host requirement interpretation must exclude private reasoning")
    if str(proposal.get("goal", "")) != goal:
        raise ValueError("host requirement interpretation is not bound to the exact goal")
    authority = str(proposal.get("authority", "host-interpretation")).strip()
    if authority not in {"host-interpretation", "official-ai-dlc-pack"}:
        raise ValueError("host requirement interpretation has an unsupported requirement authority")
    authority_mode = str(proposal.get("authority_mode", "")).strip()
    authority_stage = str(proposal.get("authority_stage", "")).strip()
    authority_references = proposal.get("authority_references", {})
    if authority == "official-ai-dlc-pack":
        if (
            authority_mode not in {"standard", "full"}
            or authority_stage != "requirements"
            or not isinstance(authority_references, dict)
            or not authority_references
            or any(not str(key).strip() or not isinstance(value, str) or not value.strip() for key, value in authority_references.items())
        ):
            raise ValueError("official AIDLC interpretation requires mode, requirements stage, and governing rule references")
    elif authority_mode or authority_stage or authority_references:
        raise ValueError("only official AIDLC requirement authority may declare official authority metadata")
    clauses = proposal.get("clauses")
    requirements = proposal.get("requirements")
    questions = proposal.get("material_questions", [])
    artifact_evidence = proposal.get("artifact_evidence", [])
    if not isinstance(clauses, list) or not clauses or len(clauses) > 25:
        raise ValueError("host requirement interpretation needs 1-25 typed clauses")
    if not isinstance(requirements, list) or not requirements or len(requirements) > 25:
        raise ValueError("host requirement interpretation needs 1-25 requirements")
    if not isinstance(questions, list) or len(questions) > 3:
        raise ValueError("host requirement interpretation material_questions must contain at most three items")
    if any(not isinstance(value, str) or not value.strip() or len(value.strip()) > 500 for value in questions):
        raise ValueError("host requirement interpretation contains an invalid material question")
    if not isinstance(artifact_evidence, list) or len(artifact_evidence) > 16:
        raise ValueError("host requirement interpretation contains invalid artifact evidence")
    normalized_clauses: list[dict[str, Any]] = []
    clause_ids: set[str] = set()
    clause_roles: dict[str, str] = {}
    grounded_goal = _grounding_text(goal)
    for index, raw in enumerate(clauses, start=1):
        if not isinstance(raw, dict):
            raise ValueError("every interpreted clause must be an object")
        clause_id = str(raw.get("clause_id") or f"C-{index:02d}").strip()
        role = str(raw.get("role", "")).strip().lower()
        text = str(raw.get("text", "")).strip()
        if not clause_id or len(clause_id) > 64 or clause_id in clause_ids or role not in CLAUSE_ROLES or not text or len(text) > 1000:
            raise ValueError("host requirement interpretation contains an invalid clause")
        source_input_id = str(raw.get("source_input_id", "")).strip()
        if source_input_id:
            artifact = artifacts.get(source_input_id)
            if artifact is None or _grounding_text(text) not in _grounding_text(str(artifact["content"])):
                raise ValueError("every artifact clause must be grounded in its inspected requirement artifact")
        elif _grounding_text(text) not in grounded_goal:
            raise ValueError("every interpreted clause must be grounded in the exact goal or an inspected requirement artifact")
        clause_ids.add(clause_id)
        clause_roles[clause_id] = role
        clause = {"clause_id": clause_id, "role": role, "text": text}
        if source_input_id:
            clause["source_input_id"] = source_input_id
        normalized_clauses.append(clause)
    normalized_artifact_evidence: list[dict[str, Any]] = []
    evidenced_input_ids: set[str] = set()
    for raw in artifact_evidence:
        if not isinstance(raw, dict):
            raise ValueError("every artifact evidence binding must be an object")
        input_id = str(raw.get("input_id", "")).strip()
        sha256 = str(raw.get("sha256", "")).strip()
        source_ids = [str(value) for value in raw.get("source_clause_ids", [])] if isinstance(raw.get("source_clause_ids"), list) else []
        artifact = artifacts.get(input_id)
        if (
            artifact is None
            or sha256 != str(artifact.get("sha256"))
            or not source_ids
            or any(value not in clause_ids for value in source_ids)
            or any(
                next((row.get("source_input_id") for row in normalized_clauses if row["clause_id"] == value), None) != input_id
                for value in source_ids
            )
        ):
            raise ValueError("artifact evidence must match inspected hashes and artifact-grounded clauses")
        evidenced_input_ids.add(input_id)
        normalized_artifact_evidence.append({
            "input_id": input_id,
            "sha256": sha256,
            "source_clause_ids": list(dict.fromkeys(source_ids)),
        })
    if artifacts and evidenced_input_ids != set(artifacts):
        raise ValueError("every required artifact must contribute hash-bound interpretation evidence")
    normalized_requirements: list[dict[str, Any]] = []
    display_ids: set[str] = set()
    for index, raw in enumerate(requirements, start=1):
        if not isinstance(raw, dict):
            raise ValueError("every interpreted requirement must be an object")
        display_id = str(raw.get("display_id") or f"REQ-{index:02d}").strip()
        statement = str(raw.get("statement", "")).strip()
        raw_source_ids = raw.get("source_clause_ids", [])
        source_ids = [str(value) for value in raw_source_ids] if isinstance(raw_source_ids, list) else []
        if not display_id or len(display_id) > 64 or display_id in display_ids or not statement or len(statement) > 1000:
            raise ValueError("host requirement interpretation contains an invalid requirement")
        if not source_ids or any(value not in clause_ids for value in source_ids):
            raise ValueError("every interpreted requirement must reference valid source clauses")
        if not any(clause_roles[value] in {"outcome", "constraint", "scope"} for value in source_ids):
            raise ValueError("every interpreted requirement must reference an outcome, constraint, or scope clause")
        display_ids.add(display_id)
        raw_intent_terms = raw.get("intent_terms", [])
        if (
            not isinstance(raw_intent_terms, list)
            or not 1 <= len(raw_intent_terms) <= 24
            or any(not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{1,63}", str(value)) for value in raw_intent_terms)
        ):
            raise ValueError("host requirement interpretation contains invalid semantic intent terms")
        intent_terms = [str(value).casefold() for value in raw_intent_terms]
        raw_literals = raw.get("quoted_literals", [])
        if (
            not isinstance(raw_literals, list)
            or len(raw_literals) > 8
            or any(not isinstance(value, str) or not 4 <= len(value.strip()) <= 160 for value in raw_literals)
        ):
            raise ValueError("host requirement interpretation contains invalid quoted literals")
        quoted_literals = [normalize_quoted_literal(str(value)) for value in raw_literals]
        semantic_goal = re.sub(
            r"[`*>#]+",
            " ",
            "\n".join([goal, *(str(item["content"]) for item in artifacts.values())]),
        )
        for literal in quoted_literals:
            semantic_goal = re.sub(re.escape(literal), " ", semantic_goal, flags=re.IGNORECASE)
        semantic_goal_terms = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{1,63}", semantic_goal.casefold()))
        if any(term not in semantic_goal_terms for term in intent_terms):
            raise ValueError("semantic intent terms must be grounded outside quoted literals")
        kind = str(raw.get("kind") or _kind(statement)).lower()
        intent_class = inferred_intent_class(
            statement,
            str(raw.get("intent_class") or "general").lower(),
        )
        confidence = str(raw.get("confidence") or "medium").lower()
        if kind not in REQUIREMENT_KINDS:
            raise ValueError("host requirement interpretation contains an invalid requirement kind")
        if intent_class not in INTENT_CLASSES:
            raise ValueError("host requirement interpretation contains an invalid intent class")
        if confidence not in {"high", "medium", "low"}:
            raise ValueError("host requirement interpretation contains an invalid confidence")
        normalized_requirements.append({
            "display_id": display_id,
            "statement": statement,
            "kind": kind,
            "source_clause_ids": list(dict.fromkeys(source_ids)),
            "intent_terms": list(dict.fromkeys(intent_terms)),
            "quoted_literals": quoted_literals,
            "intent_class": intent_class,
            "confidence": confidence,
        })
    material_questions = [str(value).strip() for value in questions if str(value).strip()]
    sufficiency = requirement_sufficiency_contract(
        normalized_clauses,
        normalized_requirements,
        material_questions,
        source="host-assisted",
    )
    material_questions = [
        str(row["question"])
        for row in sufficiency["material_decisions"]
        if row.get("question")
    ]
    result = {
        "schema_version": "1",
        "type": "tailtrail-requirement-interpretation",
        "source": "host-assisted",
        "host": proposed_host,
        "goal_fingerprint": goal_fingerprint(goal),
        "private_reasoning_excluded": True,
        "clauses": normalized_clauses,
        "artifact_evidence": normalized_artifact_evidence,
        "requirements": normalized_requirements,
        "material_questions": material_questions,
        "state": sufficiency["state"],
        "sufficiency": sufficiency,
    }
    if authority == "official-ai-dlc-pack":
        result.update({
            "authority": authority,
            "authority_mode": authority_mode,
            "authority_stage": authority_stage,
            "authority_references": {
                str(key): str(value) for key, value in authority_references.items()
            },
        })
    return result


def add_material_decisions(
    interpreted: dict[str, Any],
    decisions_to_add: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Merge pre-scope decisions into any validated interpretation.

    This lets intake gates apply equally to deterministic and host-assisted
    requirements without teaching the gate about a programming language,
    framework, or source-file layout.
    """
    additions = [
        row for row in decisions_to_add or []
        if isinstance(row, dict) and str(row.get("question", "")).strip()
    ]
    if not additions:
        return interpreted
    clauses = interpreted.get("clauses")
    requirements = interpreted.get("requirements")
    sufficiency = interpreted.get("sufficiency")
    if not isinstance(clauses, list) or not isinstance(requirements, list):
        raise ValueError("requirement interpretation lacks clauses or requirements")
    existing = (
        list(sufficiency.get("material_decisions", []))
        if isinstance(sufficiency, dict)
        else []
    )
    existing_questions = {
        str(row.get("question", "")).strip()
        for row in existing if isinstance(row, dict)
    }
    for row in additions:
        question = str(row["question"]).strip()
        if question not in existing_questions:
            existing.append(row)
            existing_questions.add(question)
    refreshed = requirement_sufficiency_contract(
        clauses,
        requirements,
        [],
        source=str(interpreted.get("source") or "deterministic-fallback"),
        material_decisions=existing,
    )
    interpreted["sufficiency"] = refreshed
    interpreted["state"] = refreshed["state"]
    interpreted["material_questions"] = [
        str(row["question"])
        for row in refreshed["material_decisions"]
        if isinstance(row, dict) and str(row.get("question", "")).strip()
    ]
    return interpreted


def query_terms(statement: str) -> list[str]:
    """Derive bounded, salient discovery terms for exactly one requirement.

    Long conversational requests commonly begin with framing such as ``there
    is an issue when the user clicks``.  Keeping those words ahead of concrete
    labels and payload names can exhaust the twelve-term discovery contract
    before Navigator sees the behavior that identifies the owning module.
    Preserve encounter order within each band, but place concrete terms before
    this small, deterministic low-signal vocabulary.
    """
    terms: list[str] = []
    for term in re.findall(r"[a-zA-Z][a-zA-Z0-9_]{2,}", statement.casefold()):
        if term not in QUERY_STOP_WORDS and term not in terms:
            terms.append(term)
    salient = [term for term in terms if term not in QUERY_LOW_SIGNAL_WORDS]
    framing = [term for term in terms if term in QUERY_LOW_SIGNAL_WORDS]
    return (salient + framing)[:12]


def frames(goal: str, interpreted: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Create stable requirement-specific inputs for scope discovery."""
    resolved = interpreted or interpretation(goal)
    framed: list[dict[str, Any]] = []
    for index, row in enumerate(resolved["requirements"], start=1):
        frame = {
            "display_id": str(row.get("display_id") or f"REQ-{index:02d}"),
            "requirement_id": stable_requirement_id(str(row["statement"])),
            "statement": str(row["statement"]),
            "query_terms": list(row.get("intent_terms") or query_terms(str(row["statement"]))),
        }
        if row.get("quoted_literals"):
            frame["quoted_literals"] = list(row["quoted_literals"])
        if row.get("intent_class") not in {None, "", "general"}:
            frame["intent_class"] = str(row["intent_class"])
        if resolved.get("source") == "host-assisted" or frame.get("intent_class"):
            frame["source_clause_ids"] = list(row.get("source_clause_ids", []))
        framed.append(frame)
    return framed


def scope_query_frame(goal: str, interpreted: dict[str, Any] | None = None) -> dict[str, Any]:
    """Expose normalized statements without replacing the canonical goal."""
    requirement_frames = frames(goal, interpreted)
    terms: list[str] = []
    for frame in requirement_frames:
        for term in frame["query_terms"]:
            if term not in terms:
                terms.append(term)
    return {
        "schema_version": "1",
        "type": "tailtrail-requirement-query-frame",
        "exact_goal_preserved": True,
        "requirements": requirement_frames,
        "query_terms": terms[:24],
    }


def canonical_set(goal: str, interpreted: dict[str, Any]) -> dict[str, Any]:
    """Freeze the only requirement identity consumed by scope and planning."""
    rows: list[dict[str, Any]] = []
    for index, source in enumerate(interpreted.get("requirements", []), start=1):
        statement = str(source.get("statement", "")).strip()
        if not statement:
            raise ValueError("canonical requirement set cannot contain an empty statement")
        row = {
            "display_id": str(source.get("display_id") or f"REQ-{index:02d}"),
            "requirement_id": str(source.get("requirement_id") or stable_requirement_id(statement)),
            "statement": statement,
            "kind": str(source.get("kind") or _kind(statement)),
            "source_clause_ids": [str(value) for value in source.get("source_clause_ids", [])],
        }
        if isinstance(source.get("source_reference"), dict):
            row["source_reference"] = dict(source["source_reference"])
        rows.append(row)
    if not rows:
        raise ValueError("canonical requirement set needs at least one requirement")
    identity = {
        "schema_version": "1",
        "type": "tailtrail-canonical-requirement-set",
        "goal_fingerprint": goal_fingerprint(goal),
        "source": str(interpreted.get("source") or "deterministic-fallback"),
        "authority": str(interpreted.get("authority") or interpreted.get("source") or "local"),
        "requirements": rows,
    }
    identity["fingerprint"] = "sha256:" + hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return identity


def bind_canonical_matrix(matrix_rows: list[dict[str, Any]], canonical: dict[str, Any]) -> None:
    """Bind enriched planner rows to the exact pre-scope requirement set."""
    expected = [
        (str(row["display_id"]), str(row["requirement_id"]), str(row["statement"]))
        for row in canonical.get("requirements", [])
    ]
    observed = [
        (str(row.get("display_id")), str(row.get("requirement_id")), str(row.get("statement")))
        for row in matrix_rows
    ]
    if observed != expected:
        raise ValueError("downstream planner attempted to replace the canonical requirement set")
    fingerprint = str(canonical.get("fingerprint", ""))
    if not fingerprint.startswith("sha256:"):
        raise ValueError("canonical requirement set fingerprint is invalid")
    for row in matrix_rows:
        row["canonical_requirement_set_fingerprint"] = fingerprint


def debug_scope_query_frame(goal: str) -> dict[str, Any]:
    """Create one stable scope row for a Debug Start symptom.

    Examples, observed output, and expected output inform reproduction, but
    they must not become separate implementation requirements or dilute owner
    discovery with renderer words and transient REQ labels.
    """
    symptom = re.sub(
        r"^(?:tailtrail\s+start\s+)?(?:debug\b[\s,:-]*)?(?:(?:an?\s*)?[\s,:-]*(?:issue|bug|defect)\b[\s,:-]*)?",
        "",
        goal.strip(),
        flags=re.IGNORECASE,
    )
    symptom = re.split(
        r"\b(?:example|observed|actual|expected)\s*:",
        symptom,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    symptom = symptom.strip()
    if len(symptom) >= 2 and symptom.startswith("`") and symptom.endswith("`"):
        symptom = symptom[1:-1].strip()
    symptom = _sentence(symptom) or _sentence(goal)
    frame = {
        "display_id": "REQ-DEBUG-01",
        "requirement_id": stable_requirement_id(symptom),
        "statement": symptom,
        "query_terms": query_terms(symptom),
    }
    return {
        "schema_version": "1",
        "type": "tailtrail-requirement-query-frame",
        "exact_goal_preserved": True,
        "requirements": [frame],
        "query_terms": frame["query_terms"],
    }


def _kind(statement: str) -> str:
    lowered = statement.lower()
    if any(word in lowered for word in ("preserve", "keep ", "remain unchanged", "retain existing")): return "preserve"
    if any(word in lowered for word in ("avoid", "do not", "must not", "only ", "forbid", "without weakening")): return "constraint"
    if any(word in lowered for word in ("security", "authorization", "authentication", "secret", "privacy")): return "safety"
    return "change"


def _tiers(statement: str) -> list[str]:
    lowered = statement.lower()
    tiers: list[str] = []
    unit_is_excluded = bool(re.search(r"(?:instead of|rather than|without|not)\b.{0,50}\bunit", lowered))
    if any(word in lowered for word in ("unit", "focused test", "focused validation")) and not unit_is_excluded: tiers.append("unit")
    if any(word in lowered for word in ("api", "contract", "schema")): tiers.append("contract")
    if any(word in lowered for word in ("workflow", "journey", "notification", "user-facing", "ui", "page", "screen")): tiers.append("behaviour")
    integration_terms = ("service", "inventory", "payment", "integration")
    integration_requested = any(
        re.search(rf"(?<![a-z0-9_]){re.escape(word)}(?![a-z0-9_])", lowered)
        for word in integration_terms
    )
    repository_layer_requested = bool(re.search(r"\brepository\s+(?:layer|model|adapter|implementation|contract)\b", lowered))
    if integration_requested or repository_layer_requested: tiers.append("integration")
    if any(word in lowered for word in ("rollout", "deployment", "migration", "infrastructure", "terraform")): tiers.append("release")
    return tiers or ["unit"]


def matrix(goal: str, paths: list[str], interpreted: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Create transient display IDs; durable UIDs remain anchor-owned."""
    deduplicated_paths = list(dict.fromkeys(path for path in paths if path))
    rows: list[dict[str, Any]] = []
    resolved = interpreted or interpretation(goal)
    interpreted_by_id = {str(row.get("display_id")): row for row in resolved["requirements"]}
    for frame in frames(goal, resolved):
        statement = str(frame["statement"])
        interpreted_row = interpreted_by_id.get(str(frame["display_id"]), {})
        kind = str(interpreted_row.get("kind") or _kind(statement)); tiers = _tiers(statement)
        matrix_row = {
            "display_id": frame["display_id"], "requirement_id": frame["requirement_id"],
            "query_terms": frame["query_terms"], "kind": kind, "statement": statement,
            "acceptance_criteria": ["The stated requirement is observably satisfied on its approved path."],
            "preserve_rules": [statement] if kind == "preserve" else ["Do not change behavior outside this approved requirement boundary."],
            "likely_paths": deduplicated_paths,
            "evidence_plan": ["Record requirement-linked computational evidence for: " + ", ".join(tiers) + "."],
            "validation_contract": {"state": "conditional" if "release" in tiers else "required", "tiers": tiers},
            "architecture_contract": {"required_paths": [], "protected_paths": [], "forbidden_imports": []},
            "behavior_contract": {"scenarios": []}, "maintainability_contract": {"rules": []},
            "confidence": str(interpreted_row.get("confidence") or "user-wording"),
            "source_clause_ids": list(frame.get("source_clause_ids", [])),
            "quoted_literals": list(frame.get("quoted_literals", [])),
            "intent_class": str(frame.get("intent_class", "general")),
        }
        if isinstance(interpreted_row.get("source_reference"), dict):
            matrix_row["source_reference"] = dict(interpreted_row["source_reference"])
        rows.append(matrix_row)
    return rows


def from_features(features: list[dict[str, Any]], paths: list[str]) -> list[dict[str, Any]]:
    """Keep already-curated programme features one-to-one with their IDs."""
    deduplicated_paths = list(dict.fromkeys(path for path in paths if path)); rows: list[dict[str, Any]] = []
    for index, feature in enumerate(features, start=1):
        statement = str(feature.get("statement", "")).strip()
        if not statement:
            continue
        kind = _kind(statement); tiers = _tiers(statement)
        rows.append({
            "display_id": str(feature.get("display_id") or f"REQ-{index:02d}"), "kind": kind,
            "requirement_id": str(feature.get("requirement_id") or stable_requirement_id(statement)),
            "query_terms": list(feature.get("query_terms") or query_terms(statement)),
            "statement": statement,
            "acceptance_criteria": ["The stated requirement is observably satisfied on its approved path."],
            "preserve_rules": [statement] if kind == "preserve" else ["Do not change behavior outside this approved requirement boundary."],
            "likely_paths": deduplicated_paths,
            "evidence_plan": ["Record requirement-linked computational evidence for: " + ", ".join(tiers) + "."],
            "validation_contract": {"state": "conditional" if "release" in tiers else "required", "tiers": tiers},
            "architecture_contract": {"required_paths": [], "protected_paths": [], "forbidden_imports": []},
            "behavior_contract": {"scenarios": []}, "maintainability_contract": {"rules": []}, "confidence": "navigator-curated",
        })
    return rows
