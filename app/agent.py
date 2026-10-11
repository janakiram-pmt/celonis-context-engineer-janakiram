"""ReAct agent on Gemini: reason, call a tool, observe, repeat; finish with an accepted briefing.

Control flow (explicit state in `Session`):
  detect (check_stock_risk) -> investigate (read_context, find_changes, find_critical_suppliers)
  -> resolve (find_transfer_options, find_alternate_vendors, rank_resolution_options)
  -> report (submit_briefing, validated; one repair round if rejected).
Ends when a briefing is accepted, or after MAX_STEPS model turns.
"""

import json
import time
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*OpenSSL.*")

from google import genai  # noqa: E402
from google.genai import errors, types  # noqa: E402

from app.config import DEFAULT_MODEL, setting  # noqa: E402
from app.tools import TOOLS, Session  # noqa: E402

MAX_STEPS = 20
MAX_REJECTIONS = 2

SYSTEM = """You are a procurement risk agent for a manufacturer. Each run you check supply risk on your own and \
send one briefing to the planners (Maria, materials planning; Tom, procurement operations).

How to work:
1. Read context-model/index.md first with read_context. It tells you what the data means and where the rules are.
2. Call check_stock_risk to find what is at risk. Stay quiet about healthy material-plants (rules/alerting.md).
3. For each Critical item, understand why (the `why` field, find_changes) and read the rules you need \
(rules/resolution-order.md, rules/vendor-eligibility.md, rules/transfer-limit.md, rules/spending-policy.md).
4. Look at the options (find_transfer_options, find_alternate_vendors), then call rank_resolution_options. \
Recommend exactly its primary plan and its fallback. Do not invent or resize actions.
5. Finish by calling submit_briefing (rules/recommendation-output.md). Every number, date, and record id you write \
must come from a tool output; never calculate numbers yourself. If the briefing is rejected, fix the listed problems \
and submit again.

You can call several tools in one turn when they don't depend on each other (for example, reading several rule files).
The analysis date is the dataset's as-of date returned by the tools, not today's real date."""

TASK = "Run today's supply risk check and submit the briefing."


def _declarations():
    return [types.FunctionDeclaration(name=name, description=spec["description"],
                                      parameters_json_schema=spec["parameters"])
            for name, spec in TOOLS.items()]


def _generate(client, model, contents, config, retries=5):
    """Call the model, retrying temporary failures (overload, rate limit) with backoff."""
    for attempt in range(retries + 1):
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except (errors.ServerError, errors.ClientError) as e:
            if "PerDay" in str(e):
                raise RuntimeError("Gemini daily free-tier quota is used up for this model; it resets daily. "
                                   "Try again later, set GEMINI_MODEL to another model, or use --offline.") from e
            temporary = isinstance(e, errors.ServerError) or getattr(e, "code", None) == 429
            if not temporary or attempt == retries:
                raise
            time.sleep(min(60, 5 * 2 ** attempt))


def _brief(value, limit=500):
    text = json.dumps(value, default=str)
    return text if len(text) <= limit else text[:limit] + f"… ({len(text)} chars)"


def run(session=None, model=None):
    """Run the agent. Returns (session, transcript lines)."""
    key = setting("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set (see .env.example). Use --offline to run without an LLM.")
    model = model or setting("GEMINI_MODEL", DEFAULT_MODEL)
    session = session or Session()
    client = genai.Client(api_key=key)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM,
        tools=[types.Tool(function_declarations=_declarations())],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        temperature=0,
    )
    contents = [types.Content(role="user", parts=[types.Part(text=TASK)])]
    transcript = [f"# Agent run ({model})", "", f"**Task:** {TASK}", ""]
    rejections = 0

    for step in range(1, MAX_STEPS + 1):
        response = _generate(client, model, contents, config)
        candidate = response.candidates[0]
        contents.append(candidate.content)
        text = " ".join(p.text for p in candidate.content.parts or [] if p.text)
        calls = response.function_calls or []
        transcript.append(f"## Step {step}")
        if text:
            transcript += ["", f"**Reasoning:** {text.strip()}"]
        if not calls:
            transcript += ["", "_No tool call; reminded to finish with submit_briefing._", ""]
            contents.append(types.Content(role="user", parts=[types.Part(
                text="Continue. Use the tools, and finish by calling submit_briefing.")]))
            continue

        parts = []
        for call in calls:
            args = dict(call.args or {})
            result = session.call(call.name, args)
            shown = {"briefing": "…"} if call.name == "submit_briefing" else args
            transcript += ["", f"- **{call.name}**(`{json.dumps(shown)}`) → `{_brief(result)}`"]
            parts.append(types.Part.from_function_response(name=call.name, response=result))
            if call.name == "submit_briefing" and not result.get("ok", {}).get("accepted"):
                rejections += 1
        contents.append(types.Content(role="user", parts=parts))
        transcript.append("")

        if session.accepted:
            transcript.append("**Briefing accepted.**")
            break
        if rejections > MAX_REJECTIONS:
            transcript.append("**Stopped: briefing rejected too many times.**")
            break
    else:
        transcript.append(f"**Stopped: reached {MAX_STEPS} steps without an accepted briefing.**")
    return session, transcript
