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
from app.tools import ASK_TOOLS, BRIEFING_TOOLS, TOOLS, Session  # noqa: E402

MAX_STEPS = 20
MAX_REJECTIONS = 2

COMMON = """Every number, date, and record id you write must come from a tool output; never calculate numbers \
yourself. If a submission is rejected, fix the listed problems and submit again.
You can call several tools in one turn when they don't depend on each other (for example, reading several rule files).
The analysis date is the dataset's as-of date returned by the tools, not today's real date."""

BRIEFING_SYSTEM = """You are a procurement risk agent for a manufacturer. Each run you check supply risk on your own \
and send one briefing to the planners (Maria, materials planning; Tom, procurement operations).

How to work:
1. Read context-model/index.md first with read_context. It tells you what the data means and where the rules are.
2. Call check_stock_risk with no arguments to find what is at risk. Stay quiet about healthy material-plants \
(rules/alerting.md).
3. If several material-plants are Critical or Warning, plan only the first one in `findingOrder`. List every other \
one in other_findings (id, tier, shortfall, date) and tell the planners to resolve this one first, then ask for the \
next alert in chat.
4. For the alert you plan, understand why (the `why` field, find_changes) and read the rules you need \
(rules/resolution-order.md, rules/vendor-eligibility.md, rules/transfer-limit.md, rules/spending-policy.md).
5. Look at the options (find_transfer_options, find_alternate_vendors), then call rank_resolution_options. \
Recommend exactly its primary plan and its fallback. Do not invent or resize actions.
6. Finish by calling submit_briefing (rules/recommendation-output.md).
""" + COMMON

ASK_SYSTEM = """You are a procurement risk assistant. A planner (Maria or Tom) asks follow-up questions about \
supply risk. Answer only from the tools and the context model.

How to work:
1. Read context-model/index.md first with read_context if you haven't yet.
2. Use the tools that answer the question; read the rule files when the question is about why or policy.
3. For "next alert": call check_stock_risk with no arguments, take the next material-plant in `findingOrder` after the \
ones already planned in this conversation, and call rank_resolution_options for it. Transfers planned earlier in \
the conversation are reserved automatically; say so.
4. If no tool or file covers the question, say you don't know rather than guessing.
5. Finish by calling answer with a short, plain answer and its citations.
""" + COMMON

TASK = "Run today's supply risk check and submit the briefing."


def _declarations(names):
    return [types.FunctionDeclaration(name=name, description=TOOLS[name]["description"],
                                      parameters_json_schema=TOOLS[name]["parameters"])
            for name in names]


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


class Agent:
    """One conversation with the model over one tool Session."""

    def __init__(self, system, tool_names, final_tool, session=None, model=None):
        key = setting("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set (see .env.example). Use --offline to run without an LLM.")
        self.model = model or setting("GEMINI_MODEL", DEFAULT_MODEL)
        self.session = session or Session()
        self.final_tool = final_tool
        self.client = genai.Client(api_key=key)
        self.config = types.GenerateContentConfig(
            system_instruction=system,
            tools=[types.Tool(function_declarations=_declarations(tool_names))],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            temperature=0,
        )
        self.contents = []
        self.transcript = [f"# Agent run ({self.model})", ""]

    def _done(self):
        return self.session.accepted if self.final_tool == "submit_briefing" else self.session.answer

    def turn(self, message):
        """Send a user message and loop until the final tool is accepted. Returns True if it was."""
        self.contents.append(types.Content(role="user", parts=[types.Part(text=message)]))
        self.transcript += [f"**User:** {message}", ""]
        rejections = 0
        for step in range(1, MAX_STEPS + 1):
            response = _generate(self.client, self.model, self.contents, self.config)
            candidate = response.candidates[0]
            self.contents.append(candidate.content)
            text = " ".join(p.text for p in candidate.content.parts or [] if p.text)
            calls = response.function_calls or []
            self.transcript.append(f"## Step {step}")
            if text:
                self.transcript += ["", f"**Reasoning:** {text.strip()}"]
            if not calls:
                self.transcript += ["", f"_No tool call; reminded to finish with {self.final_tool}._", ""]
                self.contents.append(types.Content(role="user", parts=[types.Part(
                    text=f"Continue. Use the tools, and finish by calling {self.final_tool}.")]))
                continue

            parts = []
            for call in calls:
                args = dict(call.args or {})
                result = self.session.call(call.name, args)
                shown = {"briefing": "…"} if call.name == "submit_briefing" else args
                self.transcript += ["", f"- **{call.name}**(`{json.dumps(shown)}`) → `{_brief(result)}`"]
                parts.append(types.Part.from_function_response(name=call.name, response=result))
                if call.name == self.final_tool and not result.get("ok", {}).get("accepted"):
                    rejections += 1
            self.contents.append(types.Content(role="user", parts=parts))
            self.transcript.append("")

            if self._done():
                self.transcript += ["**Accepted.**", ""]
                return True
            if rejections > MAX_REJECTIONS:
                self.transcript += ["**Stopped: rejected too many times.**", ""]
                return False
        self.transcript += [f"**Stopped: reached {MAX_STEPS} steps without an accepted {self.final_tool}.**", ""]
        return False


def run(session=None, model=None):
    """Briefing mode. Returns (session, transcript lines)."""
    agent = Agent(BRIEFING_SYSTEM, BRIEFING_TOOLS, "submit_briefing", session, model)
    agent.turn(TASK)
    return agent.session, agent.transcript


class Chat:
    """Ask mode: several questions over one Session, so earlier plans stay reserved."""

    def __init__(self, session=None, model=None):
        self.agent = Agent(ASK_SYSTEM, ASK_TOOLS, "answer", session, model)

    def ask(self, question):
        self.agent.session.answer = None
        if self.agent.turn(question):
            return self.agent.session.answer
        return None
