"""Scholarship engine: resolve the single most beneficial waiver."""
from .. data.catalog import (MERIT_BANDS, MERIT_BANDS_DPT, MERIT_BANDS_MBA,
                             POSITION_HOLDER, program_by_code, program_by_name)


def merit_waiver(program_ref: str, percentage: float = None, cgpa: float = None,
                 position_holder: bool = False) -> dict:
    """Return the merit-based waiver for a program given marks/CGPA."""
    program = program_by_code(program_ref) or program_by_name(program_ref)
    level = program["level"] if program else "BS"
    name = program["name"] if program else program_ref

    if level == "MBA":
        if cgpa is None:
            return {"found": False, "message": "MBA merit is based on prior CGPA. Please share your CGPA."}
        for band in MERIT_BANDS_MBA:
            if cgpa >= band["min"]:
                return {"found": True, "program": name, "waiver": band["waiver"], "total": False,
                        "band": band["label"],
                        "message": f"{band['label']} -> {band['waiver']}% tuition fee waiver."}
        return {"found": True, "program": name, "waiver": 0, "total": False, "band": "Below 3.00",
                "message": "Below the qualifying CGPA for an MBA merit waiver."}

    if position_holder:
        return {"found": True, "program": name, "waiver": 100, "total": True,
                "band": POSITION_HOLDER["label"],
                "message": "Board position holders qualify for a 100% Total Fee Waiver."}

    if percentage is None:
        return {"found": False, "message": "Please share your percentage to determine the merit waiver."}

    bands = MERIT_BANDS_DPT if level == "DPT" else MERIT_BANDS
    for band in bands:
        if band["min"] <= percentage < band["max"]:
            return {"found": True, "program": name, "waiver": band["waiver"],
                    "total": band["total"], "band": band["label"],
                    "message": f"{band['label']} -> {band['waiver']}% tuition fee waiver."}
    return {"found": True, "program": name, "waiver": 0, "total": False, "band": "Below threshold",
            "message": "No merit-based waiver at this percentage; other categories may still apply."}


def best_scholarship(program_ref: str, percentage: float = None, cgpa: float = None,
                     position_holder: bool = False, category_waivers: list = None) -> dict:
    """
    Resolve the single most beneficial waiver across merit + any qualifying categories.
    category_waivers: optional list of {"name": str, "waiver": int, "total": bool}.
    Scholarships do NOT stack; the highest applicable is returned.
    """
    options = []
    m = merit_waiver(program_ref, percentage, cgpa, position_holder)
    if m.get("found"):
        options.append({"name": m["band"], "waiver": m["waiver"], "total": m.get("total", False)})
    for c in (category_waivers or []):
        options.append({"name": c["name"], "waiver": c.get("waiver", 0), "total": c.get("total", False)})

    if not options:
        return {"found": False, "message": "Not enough information to determine a scholarship yet."}

    # total fee waiver beats any percentage; otherwise highest waiver wins
    options.sort(key=lambda o: (o["total"], o["waiver"]), reverse=True)
    best = options[0]
    return {
        "found": True, "best": best, "all_options": options,
        "message": (f"Maximum scholarship: {best['name']} - "
                    + ("100% Total Fee Waiver." if best["total"] else f"{best['waiver']}% tuition fee waiver.")
                    + " Scholarships do not stack; this is the single highest you qualify for."),
    }
