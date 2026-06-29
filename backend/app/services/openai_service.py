"""LLM brain for the AI counsellor: OpenAI chat with tool-calling into the
eligibility / fee / scholarship engines, grounded by RAG over the knowledge base.
Falls back to a deterministic responder when no OpenAI key is configured."""
import json
from sqlalchemy.orm import Session
from ..config import get_setting
from ..engines import eligibility, fees, scholarships
from ..data import catalog
from . import rag

SYSTEM_PROMPT = """You are the AI Admissions Counsellor for {business}. You help applicants for the Fall 2026 intake.

GOLDEN RULES (always follow):
- Be warm, concise and accurate. Reply in the applicant's language (English or Urdu).
- Minimal disclosure: answer only what is asked. NEVER volunteer fee figures or scholarship amounts unprompted.
- Share a fee ONLY when the applicant explicitly asks; then give that one program's fee.
- When showing scholarships, state the single highest waiver they qualify for. Scholarships do NOT stack.
- Use ONLY the tools and the provided knowledge base for facts. Never invent fees, deadlines, or seat numbers.
- If a fee is "to confirm", say it is being finalised and offer the admissions office. Do not quote a number.
- If a requested program is not offered at Okara, tell them it may be available at the Superior University Lahore campus and offer to connect a counsellor.
- If unsure, frustrated, or out of scope, offer to connect a human counsellor.
- Office hours / appointments: {office_hours}. Apply online at {portal} (select Okara Campus).

Use the tools to compute eligibility, fees and scholarships rather than guessing.
Keep replies short for WhatsApp."""

TOOLS = [
    {"type": "function", "function": {
        "name": "check_eligibility",
        "description": "Check if an applicant is eligible for a program given their marks.",
        "parameters": {"type": "object", "properties": {
            "program": {"type": "string", "description": "Program name or code"},
            "obtained": {"type": "number"}, "total": {"type": "number"},
            "percentage": {"type": "number"},
            "result_awaited": {"type": "boolean", "description": "True if final result not yet declared"}},
            "required": ["program"]}}},
    {"type": "function", "function": {
        "name": "get_fee",
        "description": "Get a program's fee. Only call when the applicant explicitly asks about fee.",
        "parameters": {"type": "object", "properties": {
            "program": {"type": "string"},
            "scholarship_pct": {"type": "number", "description": "Tuition waiver % if known"}},
            "required": ["program"]}}},
    {"type": "function", "function": {
        "name": "get_scholarship",
        "description": "Resolve the maximum scholarship for a program from percentage or CGPA.",
        "parameters": {"type": "object", "properties": {
            "program": {"type": "string"}, "percentage": {"type": "number"},
            "cgpa": {"type": "number"}, "position_holder": {"type": "boolean"}},
            "required": ["program"]}}},
    {"type": "function", "function": {
        "name": "list_programs",
        "description": "List programs offered at the Okara campus, optionally filtered by faculty.",
        "parameters": {"type": "object", "properties": {
            "faculty": {"type": "string", "enum": catalog.FACULTIES}}}}},
    {"type": "function", "function": {
        "name": "save_lead",
        "description": "Save applicant details to start an application.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string"}, "cnic": {"type": "string"},
            "father_name": {"type": "string"}, "program": {"type": "string"},
            "contact_number": {"type": "string"}}, "required": ["name", "program"]}}},
]


def _run_tool(db: Session, name: str, args: dict, contact=None) -> dict:
    if name == "check_eligibility":
        return eligibility.check_eligibility(
            args.get("program"), args.get("obtained"), args.get("total"),
            args.get("percentage"), args.get("result_awaited", False))
    if name == "get_fee":
        if args.get("scholarship_pct"):
            return fees.net_first_semester(args["program"], args.get("scholarship_pct", 0))
        return fees.get_fee(args.get("program"))
    if name == "get_scholarship":
        return scholarships.best_scholarship(
            args.get("program"), args.get("percentage"), args.get("cgpa"),
            args.get("position_holder", False))
    if name == "list_programs":
        fac = args.get("faculty")
        progs = catalog.programs_by_faculty(fac) if fac else catalog.PROGRAMS
        return {"programs": [{"name": p["name"], "min_pct": p["min_pct"],
                              "qualification": p["qualification"]} for p in progs]}
    if name == "save_lead":
        if contact is not None:
            from .crm import apply_lead_details
            apply_lead_details(db, contact, args)
        return {"saved": True, "next": "Show scholarship, then offer prospectus voucher or office appointment."}
    return {"error": f"unknown tool {name}"}


def is_ai_enabled(db: Session) -> bool:
    return bool(get_setting(db, "AI_PROVIDER", "openai") == "openai" and get_setting(db, "OPENAI_API_KEY"))


def _client(db: Session):
    key = get_setting(db, "OPENAI_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=key)
    except Exception:  # noqa
        return None


def transcribe(db: Session, audio_bytes: bytes, mime: str = "audio/ogg", language: str = None):
    """Speech-to-text for an inbound voice note. Returns text or None."""
    client = _client(db)
    if not client or not audio_bytes:
        return None
    model = get_setting(db, "OPENAI_STT_MODEL", "whisper-1")
    ext = "ogg"
    if "mp3" in (mime or ""):
        ext = "mp3"
    elif "wav" in (mime or ""):
        ext = "wav"
    elif "m4a" in (mime or "") or "mp4" in (mime or ""):
        ext = "m4a"
    try:
        kwargs = {"model": model, "file": (f"audio.{ext}", audio_bytes, mime or "audio/ogg")}
        if language in ("en", "ur"):
            kwargs["language"] = language
        resp = client.audio.transcriptions.create(**kwargs)
        return (getattr(resp, "text", "") or "").strip()
    except Exception:  # noqa
        return None


def synthesize(db: Session, text: str):
    """Text-to-speech. Returns (audio_bytes, mime) as OGG/Opus (a WhatsApp voice note) or (None, None)."""
    client = _client(db)
    if not client or not text:
        return None, None
    model = get_setting(db, "OPENAI_TTS_MODEL", "tts-1")
    voice = get_setting(db, "OPENAI_TTS_VOICE", "alloy")
    try:
        resp = client.audio.speech.create(model=model, voice=voice, input=text[:4000],
                                          response_format="opus")
        if hasattr(resp, "read"):
            data = resp.read()
        elif hasattr(resp, "content"):
            data = resp.content
        else:
            data = bytes(resp)
        return data, "audio/ogg"
    except Exception:  # noqa
        return None, None


def answer(db: Session, contact, user_text: str, history: list = None) -> str:
    """Generate a grounded reply for the AI counsellor."""
    business = get_setting(db, "BUSINESS_NAME", "Superior University Okara Campus")
    system = SYSTEM_PROMPT.format(business=business, office_hours=catalog.OFFICE_HOURS,
                                  portal=catalog.APPLY_PORTAL)

    # ground with RAG
    contexts = rag.retrieve(db, user_text, k=4)
    if contexts:
        kb = "\n\n".join(f"[{c['title']}]\n{c['content']}" for c in contexts)
        system += "\n\nKNOWLEDGE BASE (authoritative, use this for facts):\n" + kb

    if not is_ai_enabled(db):
        return _fallback_answer(db, user_text, contexts)

    from openai import OpenAI
    client = OpenAI(api_key=get_setting(db, "OPENAI_API_KEY"))
    model = get_setting(db, "OPENAI_MODEL", "gpt-4o-mini")

    messages = [{"role": "system", "content": system}]
    for h in (history or [])[-8:]:
        messages.append(h)
    messages.append({"role": "user", "content": user_text})

    try:
        for _ in range(4):  # allow a few tool-call rounds
            resp = client.chat.completions.create(model=model, messages=messages,
                                                  tools=TOOLS, temperature=0.3)
            msg = resp.choices[0].message
            if msg.tool_calls:
                messages.append({"role": "assistant", "content": msg.content or "",
                                 "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    result = _run_tool(db, tc.function.name, args, contact)
                    messages.append({"role": "tool", "tool_call_id": tc.id,
                                     "content": json.dumps(result)})
                continue
            return (msg.content or "").strip() or _fallback_answer(db, user_text, contexts)
    except Exception as e:  # noqa
        return _fallback_answer(db, user_text, contexts, error=str(e))
    return _fallback_answer(db, user_text, contexts)


def _fallback_answer(db: Session, user_text: str, contexts: list, error: str = None) -> str:
    """Deterministic, grounded reply when the LLM is unavailable."""
    if contexts:
        top = contexts[0]
        snippet = top["content"]
        # trim to a friendly length
        snippet = snippet.split("\n", 1)[-1] if snippet.startswith("#") else snippet
        return (snippet[:700].strip() +
                "\n\nWould you like me to connect you with a human counsellor for more detail?")
    return ("I can help with programs, eligibility, fees, scholarships, transport and admissions at "
            f"{catalog.CAMPUS_NAME}. Could you tell me which program you're interested in? "
            "I can also connect you with a human counsellor.")
