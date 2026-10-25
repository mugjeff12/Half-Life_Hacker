"""Lesson content. Every code block is the workshop notebook's own cell (hlh/cells.py);
this file only adds the GUI text, hints, solutions and hidden auto-checks around them."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np

from . import physics_ref as ref
from .cells import CELLS
from .mathimg import eq, img
from .theme import BLACK, INK, MAROON, MAROON_TINT, MUTED, WHITE


# ----------------------------------------------------------------------------- html helpers
def callout(title: str, body: str, kind: str = "tip") -> str:
    bar, bg, fg, head = {
        "tip": (MAROON, MAROON_TINT, INK, MAROON),
        "task": (MAROON, BLACK, WHITE, "#FF8FB3"),
        "think": (BLACK, "#EFEBED", INK, BLACK),
    }[kind]
    if kind == "task":
        body = body.replace("<code>", '<code style="color:#FFFFFF;background-color:#4A0B26">')
    return (
        '<table width="100%" cellspacing="0" cellpadding="0" style="margin-top:8px;margin-bottom:8px"><tr>'
        f'<td width="6" bgcolor="{bar}"></td>'
        f'<td bgcolor="{bg}" style="padding:9px 14px"><span style="color:{head}"><b>{title}</b></span><br>'
        f'<span style="color:{fg}">{body}</span></td></tr></table>'
    )


def terms(rows) -> str:
    """rows: [(sign, tex, description)] — one aligned line per term of an equation."""
    trs = "".join(
        f'<tr><td valign="middle">{img(("+" if sg == "+" else "-") + r"\;" + t)}</td>'
        f'<td valign="middle"><span style="color:{MUTED}">&nbsp;&nbsp;&nbsp;{d}</span></td></tr>'
        for sg, t, d in rows
    )
    return f'<table cellspacing="0" cellpadding="3" style="margin:2px 0 8px 14px">{trs}</table>'


def your_turn(text: str) -> str:
    return callout("🔧 YOUR TURN", text + "<br>Press <b>▶ Run</b> (Ctrl+Enter) to test it — you'll get a ✓ or a ✗ with a hint.", "task")


# ----------------------------------------------------------------------------- model
@dataclass
class Step:
    id: str
    title: str
    kind: str                       # info | code | sim | predict | slider | final
    html: str
    code: str = ""
    solution: str = ""
    hints: list = field(default_factory=list)
    after: Optional[Callable] = None        # hidden auto-check, runs after the student's code
    done_if: Optional[Callable] = None      # extra completion condition  (ns) -> bool
    note: Optional[Callable] = None         # extra console message       (ns, extras) -> (text, kind)
    autorun: bool = False
    slider: Optional[dict] = None
    options: list = field(default_factory=list)   # for 'predict'
    correct: str = ""
    label: str = ""                 # filled in by build(), e.g. "3.4"
    section: str = ""


@dataclass
class Section:
    id: str
    title: str
    rung: str
    banner: str                     # image key in assets/img, or "" for the brand gradient
    focus: float
    steps: list


def apply_replacements(code: str, repls) -> str:
    """Surgical edits with a uniqueness assertion — a solution can never silently drift from the cell."""
    for old, new in repls:
        assert code.count(old) == 1, f"replacement target not unique/missing: {old!r}"
        code = code.replace(old, new)
    return code


def solved(cell_id: str, repls) -> str:
    return apply_replacements(CELLS[cell_id], repls)


def func_only(cell_id: str) -> str:
    """The notebook's slider cells end with an ipywidgets block; the app has native sliders instead."""
    src = CELLS[cell_id]
    return src[: src.index("\ntry:")].rstrip() + "\n"


# ----------------------------------------------------------------------------- hidden auto-checks
def ac_xenon(ns):
    f, chk = ns["xenon_system"], ns["check"]
    Sig = ref.CANDU["Sigma_f"]
    for tag, Phi in (("flux ON", ref.CANDU["Phi"]), ("after SCRAM, Φ = 0", 0.0)):
        out = f(0.0, [1e15, 1e14], Sig, lambda t, P=Phi: P)
        eI, eX = ref.xenon_rates(1e15, 1e14, Sig, Phi)
        chk(f"dN_I/dt, {tag}", out[0], eI, tol=1e-3,
            hint="I-135 is PRODUCED by fission (gamma_I * Sigma_f * Phi) and LOST by decay (lambda_I * N_I).")
        chk(f"dN_Xe/dt, {tag}", out[1], eX, tol=1e-3,
            hint="Four terms: +lambda_I*N_I  +gamma_Xe*Sigma_f*Phi  -lambda_Xe*N_Xe  -sigma_a_Xe*Phi*N_Xe. "
                 "At shutdown (Phi = 0) the last one must vanish — is it multiplied by Phi?")


def ac_shutdown(ns):
    st = ns.get("shutdown_time")
    if st is None or not np.isfinite(st):
        print("  ⏳ shutdown_time is still np.inf — the reactor never shuts down. Set it to the SCRAM time (3 days).")
        ns["__checks__"].append(("shutdown_time", "pending"))
    else:
        ns["check"]("shutdown_time (in days)", st / ref.DAY, 3, tol=1e-6, hint="3 * DAY")


def ac_waste(ns):
    f, chk = ns["waste_decay"], ns["check"]
    out = f(0.0, [1.0, 1.0])
    chk("dN_Cs/dt at N=1", out[0], -ref.lambda_Cs, tol=1e-3, hint="-lambda_Cs * N_Cs   (negative: atoms disappear)")
    chk("dN_Sr/dt at N=1", out[1], -ref.lambda_Sr, tol=1e-3, hint="-lambda_Sr * N_Sr")


def reveal_done(ns) -> bool:
    st = ns.get("shutdown_time")
    return st is not None and np.isfinite(st)


def reveal_note(ns, extras):
    """(text, kind) shown under the plot's console output."""
    guess = extras.get("prediction")
    if not guess:
        return ""
    if guess == "C":
        return ("Your team predicted (C) — correct! 🎉  Xenon really does climb after shutdown.", "ok")
    return (f"Your team predicted ({guess}) — not this time! The answer is (C): xenon climbs for hours first.", "warn")


# ----------------------------------------------------------------------------- solutions (surgical replacements)
# Starter code shown to students: the notebook cell minus anything that spells out the answer
# (the Hint and Solution buttons are where answers live). Each target must match exactly once.
SCRUB = {
    "b752111c": [
        ("#    Formula:  lambda = ln(2) / half-life      (ln(2) is written np.log(2))\n",
         "#    Use the half-life \u2192 decay-constant relationship from the lesson.\n"),
        ('hint="np.log(2) / t_half_I"', 'hint="decay constant from the half-life (see the lesson)"'),
    ],
    "358ff59c": [
        ("TODO-EASY-2:  dN/dt = -lambda * N", "TODO-EASY-2:  write dN/dt for this isotope"),
        ("atoms are disappearing: -lam * n", "atoms are disappearing"),
    ],
    "91c9ffd8": [
        ('hint="-lam_parent * N_parent"', 'hint="the parent only loses atoms, through its own decay"'),
        ('hint="lam_parent*N_parent - lam_daughter*N_daughter  (daughter starts at 0)"',
         'hint="the daughter gains from the parent and loses by its own decay (it starts at 0)"'),
    ],
    "1382e86d": [
        ("    #   production = gamma_I * Sigma_f * Phi      loss = lambda_I * N_I\n", ""),
        ("    #   + from I-135 decay     :  lambda_I * N_I\n", "    #   + from I-135 decay\n"),
        ("    #   + direct from fission  :  gamma_Xe * Sigma_f * Phi\n", "    #   + direct from fission\n"),
        ("    #   - its own decay        :  lambda_Xe * N_Xe\n", "    #   - its own decay\n"),
        ("    #   - eaten by neutrons    :  sigma_a_Xe * Phi * N_Xe\n", "    #   - eaten by neutrons (absorption)\n"),
    ],
    "489abcde": [
        ("change np.inf to  3 * DAY  to SCRAM the reactor at t = 3 days.",
         "SCRAM the reactor at t = 3 days by changing this one value (DAY is defined for you)."),
    ],
    "d9e5e4eb": [
        ("    # \U0001F527 TODO-EXT-A: return  0.066 * ( t**(-0.2) - (t + T_op)**(-0.2) )\n",
         "    # \U0001F527 TODO-EXT-A: return the Way\u2013Wigner decay-heat fraction (formula in the lesson)\n"),
        ('hint="0.066 * (t**(-0.2) - (t + T_op)**(-0.2))"', 'hint="two power-law terms, subtracted, times 0.066"'),
    ],
    "ee4b8746": [
        ("    dN_Cs_dt = None      # -lambda_Cs * N_Cs", "    dN_Cs_dt = None"),
        ("    dN_Sr_dt = None      # -lambda_Sr * N_Sr", "    dN_Sr_dt = None"),
    ],
}

SOL = {
    "b752111c": [("lambda_I  = None     # <- replace None", "lambda_I  = np.log(2) / t_half_I"),
                 ("lambda_Xe = None     # <- replace None", "lambda_Xe = np.log(2) / t_half_Xe")],
    "358ff59c": [("    dn_dt = None ", "    dn_dt = -lam * n ")],
    "91c9ffd8": [("    dN_parent_dt   = None", "    dN_parent_dt   = -lam_parent * N_parent"),
                 ("    dN_daughter_dt = None",
                  "    dN_daughter_dt = lam_parent * N_parent - lam_daughter * N_daughter")],
    "1382e86d": [("    dN_I_dt  = None", "    dN_I_dt  = gamma_I * Sigma_f * Phi - lambda_I * N_I"),
                 ("    dN_Xe_dt = None",
                  "    dN_Xe_dt = (lambda_I * N_I + gamma_Xe * Sigma_f * Phi\n"
                  "                - lambda_Xe * N_Xe - sigma_a_Xe * Phi * N_Xe)")],
    "489abcde": [("shutdown_time = np.inf      # <- change", "shutdown_time = 3 * DAY     # <- change")],
    "d9e5e4eb": [("    return None\n", "    return 0.066 * (t**(-0.2) - (t + T_op)**(-0.2))\n")],
    "ee4b8746": [("    dN_Cs_dt = None", "    dN_Cs_dt = -lambda_Cs * N_Cs"),
                 ("    dN_Sr_dt = None", "    dN_Sr_dt = -lambda_Sr * N_Sr")],
}


def todo(cell_id: str) -> dict:
    start = apply_replacements(CELLS[cell_id], SCRUB.get(cell_id, []))
    return dict(code=start, solution=apply_replacements(start, SOL[cell_id]))


# ----------------------------------------------------------------------------- the lesson
def build() -> list:
    P = []   # sections

    # ================================================================== WELCOME
    welcome = Section("welcome", "Welcome", "", "people", 0.55, [
        Step("welcome", "Mission briefing", "info", (
            "<h1>☢️ Half-Life Hacker</h1>"
            "<h3>Simulating fission product decay chains and their consequences</h3>"
            "<p><b>You are a nuclear safety analyst.</b> A reactor has just shut down. The chain reaction has "
            "stopped — but the core is still pouring out heat, and an invisible isotope is about to make the "
            "reactor <i>harder</i> to restart, not easier. Your job today is to model exactly what is happening, "
            "from scratch, in Python.</p>"
            "<p>You will build up to it in five rungs:</p>"
            '<table width="100%" cellspacing="0" cellpadding="7" style="margin:4px 0 10px 0">'
            f'<tr bgcolor="{BLACK}"><td><span style="color:{WHITE}"><b>Rung</b></span></td>'
            f'<td><span style="color:{WHITE}"><b>What you model</b></span></td>'
            f'<td><span style="color:{WHITE}"><b>The question it answers</b></span></td></tr>'
            f'<tr><td>1</td><td>A single decaying isotope</td><td>How fast does radioactivity fade?</td></tr>'
            f'<tr bgcolor="#F4F0F2"><td>2</td><td>A parent → daughter chain</td><td>How is one isotope born from another?</td></tr>'
            f'<tr><td>3</td><td>The <b>I-135 → Xe-135</b> reactor system</td><td><i>Why does xenon climb after shutdown?</i></td></tr>'
            f'<tr bgcolor="#F4F0F2"><td>4</td><td>Shutdown <b>decay heat</b></td><td>Why can\'t you ever turn the cooling off?</td></tr>'
            f'<tr><td>5</td><td>Long-lived waste (Cs-137, Sr-90)</td><td>Why ~300 years of isolation?</td></tr></table>'
            "<h3>How this app works</h3>"
            "<ul>"
            "<li>Work down the <b>sidebar</b> in order (or hit <b>Next ▶</b>). Your work saves automatically.</li>"
            "<li>Steps marked <b>🔧 YOUR TURN</b> have a <b>TODO</b> in the code editor — those are the lines "
            "<i>you</i> write. Everything else is given.</li>"
            "<li>You only ever write <b>physics</b> (a rate, a decay constant, a source term). The plotting, the "
            "solver and the plumbing are already done for you.</li>"
            "<li>After a task you get <b>✓</b> (correct) or <b>✗</b> (try again, with a hint). Stuck? "
            "<b>💡 Hint</b> gives progressively bigger nudges.</li>"
            "<li><b>Never coded before?</b> That's expected. The first task is one line. You've got this.</li>"
            "<li>Projector? <b>Ctrl +</b> / <b>Ctrl −</b> zoom the text, <b>F11</b> goes full-screen.</li>"
            "</ul>"
        )),
        Step("data", "The physics data table", "sim", (
            "<h1>The physics data table</h1>"
            "<p>Every number a real analyst would look up, with units in the comments. This table is already "
            "loaded for you — you will <i>reference</i> these names throughout; you don't need to change anything.</p>"
            + callout("Worth a look", "<b>σ<sub>a</sub>(Xe-135) = 2.65 million barns.</b> For scale, U-235 fission is "
                      "about 580 barns — Xe-135 looks ~4500× bigger to a neutron. Keep that number in mind.", "think") +
            "<p>Two reactor “personalities” are defined at the bottom: an <b>LWR</b> and a <b>CANDU</b>. "
            "Their flux Φ and macroscopic fission cross-section Σ<sub>f</sub> are <i>representative</i> values, chosen "
            "so each power density comes out right (LWR ≈ 96 kW/L, CANDU ≈ 12 kW/L).</p>"
            "<p>Press <b>▶ Run</b> to (re)load it.</p>"),
            code=CELLS["3acb2a6a"], autorun=True),
    ])
    P.append(welcome)

    # ================================================================== 1  SINGLE ISOTOPE
    s1 = Section("s1", "A Single Decaying Isotope", "Rung 1", "sign", 0.45, [
        Step("s1-idea", "The idea", "info", (
            "<h1>A single decaying isotope</h1>"
            "<p><b>Analyst's question:</b> your detector shows a sample of pure I-135. How fast does it fade?</p>"
            "<p>Radioactive decay is random, but huge numbers of atoms average out to a clean law. If every atom has "
            "the same tiny probability <b>λ</b> (“lambda”) of decaying per second, then the number of atoms <b>N</b> "
            "falls at a rate proportional to how many are left:</p>"
            + eq(r"\frac{dN}{dt} = -\lambda N") + eq(r"N(t) = N_0\,e^{-\lambda t}") +
            "<p>The decay constant λ is tied to the <b>half-life</b> t<sub>½</sub> (time for half to decay):</p>"
            + eq(r"\lambda = \frac{\ln 2}{t_{1/2}}") +
            "<p><i>(In Python, the natural log “ln” is written <code>np.log</code>.)</i></p>")),
        Step("s1-lambda", "Compute the decay constants", "code", (
            "<h1>TODO-EASY-1 · decay constants</h1>"
            "<p>This is your first line of code: <b>λ = ln 2 / t<sub>½</sub></b>. That's it.</p>"
            "<p>The half-lives <code>t_half_I</code> and <code>t_half_Xe</code> come from the data table (already in seconds).</p>"
            + your_turn("Replace each <code>None</code> with the formula.")),
            hints=["The decay constant is the natural log of 2 divided by the half-life.",
                   "In Python: <code>np.log(2) / t_half_I</code>. Do the same for Xe-135 with <code>t_half_Xe</code>."],
            **todo("b752111c")),
        Step("s1-rate", "Write the rate of change", "code", (
            "<h1>TODO-EASY-2 · the rate equation</h1>"
            "<h3>How a computer “solves” a rate equation</h3>"
            "<p>We hand the rule dN/dt = −λN to a solver (<code>solve_ivp</code>). The solver starts at N<sub>0</sub> "
            "and takes thousands of tiny time-steps, each time asking your function "
            "<i>“given N right now, how fast is it changing?”</i> — and nudging N forward. So the solver needs the "
            "physics packaged as a <b>function</b>.</p>"
            + your_turn("Fill in the single line that says <i>“atoms disappear at rate λN.”</i>")),
            hints=["The answer is negative — atoms are disappearing.",
                   "<code>dn_dt = -lam * n</code>"],
            **todo("358ff59c")),
        Step("s1-sim", "Run the simulation", "sim", (
            "<h1>▶️ Run the simulation</h1>"
            "<p>This solves <i>your</i> equation and overlays the exact analytic answer. They should land right on "
            "top of each other — that's how you know your physics is correct.</p>"
            + callout("Look for", "The left plot marks each half-life: does the curve halve every time? On the right "
                      "(log scale), a <b>straight line</b> means a pure exponential.", "think") +
            "<p>The code on the right is given — read it, it's the “lecture”. Then press <b>▶ Run</b>.</p>"),
            code=CELLS["6b81edb5"]),
        Step("s1-play", "Play: change the half-life", "slider", (
            "<h1>🎚️ Play: how does half-life change the curve?</h1>"
            "<p>Drag the slider. A short half-life → a steep cliff. A long one → a slow fade.</p>"
            "<p>Try the presets: I-135 (6.57 h) and Xe-135 (9.17 h) are the two isotopes you'll chain together next.</p>"),
            code=func_only("4c19c564"), autorun=True,
            slider=dict(func="plot_decay_for_halflife", label="Half-life t½", unit="h", lo=0.5, hi=24.0, step=0.1,
                        value=6.57, presets=[("I-135 · 6.57", 6.57), ("Xe-135 · 9.17", 9.17), ("1 h", 1.0), ("24 h", 24.0)])),
    ])
    P.append(s1)

    # ================================================================== 2  TWO-STEP CHAIN
    s2 = Section("s2", "A Two-Step Chain: I-135 → Xe-135", "Rung 2", "building", 0.5, [
        Step("s2-idea", "The Bateman pattern", "info", (
            "<h1>A two-step chain: I-135 → Xe-135</h1>"
            "<p><b>Analyst's question:</b> I-135 doesn't vanish — it <i>decays into</i> Xe-135. So while I-135 falls, "
            "Xe-135 is <i>born</i>. How do you track both at once?</p>"
            "<p>This is the <b>Bateman pattern</b> in miniature. Each isotope obeys:</p>"
            + callout("The pattern", "<b>rate of change = (gain from your parent) − (loss by your own decay)</b>", "tip") +
            "<p>For our two-step chain (no reactor yet, just decay):</p>"
            + eq(r"\frac{dN_I}{dt} = -\lambda_I N_I") + eq(r"\frac{dN_{Xe}}{dt} = \lambda_I N_I - \lambda_{Xe} N_{Xe}") +
            terms([("+", r"\lambda_I N_I", "born from I-135 decaying"), ("−", r"\lambda_{Xe} N_{Xe}", "Xe-135's own decay")]) +
            "<p>I-135 has <b>no parent here</b>, so it only loses. Xe-135 <b>gains from I-135 and loses by decaying.</b> "
            "Remember this shape — you'll write it again, with extra terms, for the real reactor.</p>")),
        Step("s2-code", "Write both coupled rates", "code", (
            "<h1>TODO-MEDIUM-1 &amp; 2 · coupled rates</h1>"
            "<p><code>dN_parent</code> reuses exactly what you did earlier. <code>dN_daughter</code> adds <b>one new "
            "idea</b>: a gain term from the parent.</p>"
            "<p>Inside the function, <code>N_parent</code> is I-135 and <code>N_daughter</code> is Xe-135.</p>"
            + your_turn("Write both lines. The daughter has a <b>+</b> term and a <b>−</b> term.")),
            hints=["The parent only loses atoms: minus its decay constant times its own atom count.",
                   "The daughter's gain is the <i>parent's</i> decay rate: <code>lam_parent * N_parent</code>.",
                   "<code>dN_daughter_dt = lam_parent * N_parent - lam_daughter * N_daughter</code>"],
            **todo("91c9ffd8")),
        Step("s2-sim", "Watch Xe-135 grow, then fade", "sim", (
            "<h1>▶️ Watch Xe-135 grow, then fade</h1>"
            "<p>Start with pure I-135 and no Xe-135. The daughter <b>ingrows</b> (rises as the parent feeds it), peaks, "
            "then decays once the parent runs low.</p>"
            + callout("Why this matters", "This <i>ingrowth-then-decay</i> hump is the seed of the big surprise in the next section.", "tip")),
            code=CELLS["55673826"]),
    ])
    P.append(s2)

    # ================================================================== 3  REACTOR
    s3 = Section("s3", "The Reactor: I-135 / Xe-135 with Flux", "Rung 3", "core", 0.5, [
        Step("s3-idea", "Put the chain in a reactor", "info", (
            "<h1>⭐ The reactor: I-135 / Xe-135 with neutron flux</h1>"
            "<p><b>This is the heart of the workshop.</b> Now put the chain <i>inside an operating reactor</i>. "
            "Two things change:</p>"
            "<ol><li><b>Fission keeps making fresh I-135 and Xe-135.</b> Every fission has a yield (γ) of each.</li>"
            "<li><b>Xe-135 is devoured by neutrons.</b> It is the strongest thermal-neutron absorber known — "
            "2.65 <i>million</i> barns. While the reactor runs, neutrons burn Xe-135 away almost as fast as it forms.</li></ol>"
            + eq(r"\frac{dN_I}{dt} = \gamma_I\,\Sigma_f\,\Phi - \lambda_I N_I") +
            terms([("+", r"\gamma_I\,\Sigma_f\,\Phi", "I-135 from fission"), ("−", r"\lambda_I N_I", "decay")]) +
            eq(r"\frac{dN_{Xe}}{dt} = \lambda_I N_I + \gamma_{Xe}\Sigma_f\Phi - \lambda_{Xe} N_{Xe} - \sigma_a^{Xe}\,\Phi\, N_{Xe}") +
            terms([("+", r"\lambda_I N_I", "from I-135 decaying"),
                   ("+", r"\gamma_{Xe}\,\Sigma_f\,\Phi", "direct from fission"),
                   ("−", r"\lambda_{Xe}\,N_{Xe}", "its own decay"),
                   ("−", r"\sigma_a^{Xe}\,\Phi\,N_{Xe}", "<b>eaten by neutrons</b>")]) +
            "<p>Here <b>Φ</b> is the neutron flux. When the reactor is running, Φ is large. <b>At shutdown, Φ → 0.</b></p>"
            + callout("Keep your eye on…", "that last term — it's the one that <b>vanishes</b> when the reactor trips.", "tip"))),
        Step("s3-pick", "Pick your reactor", "sim", (
            "<h1>Pick your reactor</h1>"
            "<p>We'll default to <b>CANDU</b> (this is a CANDU workshop) and compare with an LWR later.</p>"
            "<p>The second block defines the <b>flux schedule</b>: full power, then 0 after shutdown.</p>"
            + callout("Try it", "Change <code>REACTOR = CANDU</code> to <code>LWR</code> and press Run to switch reactors. "
                      "(Run the later steps again afterwards to see the effect.)", "think")),
            code=CELLS["ae421a60"]),
        Step("s3-xenon", "Build the reactor equations", "code", (
            "<h1>TODO-HARD-1 &amp; 2 · the reactor equations</h1>"
            "<p>Same <b>“gain − loss”</b> shape as before, but I-135 now has a fission <i>source</i>, and Xe-135 now "
            "has <b>four</b> terms. The neutron-absorption loss term is the most important one in the whole workshop — "
            "<b>don't drop it</b>.</p>"
            + your_turn("Fill in <code>dN_I_dt</code> (2 terms) and <code>dN_Xe_dt</code> (4 terms). "
                        "The comments list every term for you.")),
            hints=["I-135: one source term from fission, one loss term from its own decay.",
                   "Xe-135 gets two <b>+</b> terms and two <b>−</b> terms — the comments in the code list all four.",
                   "The neutron-absorption term is <code>sigma_a_Xe * Phi * N_Xe</code>. It must be multiplied by <code>Phi</code> so it disappears when Φ = 0."],
            after=ac_xenon, **todo("1382e86d")),
        Step("s3-eq", "Run the reactor to equilibrium", "sim", (
            "<h1>▶️ Run the reactor to equilibrium</h1>"
            "<p>With the flux on and <i>never</i> shutting down, both isotopes settle to a steady value where "
            "production balances loss — set dN/dt = 0:</p>"
            + eq(r"N_I^{eq} = \frac{\gamma_I\,\Sigma_f\,\Phi}{\lambda_I}") +
            eq(r"N_{Xe}^{eq} = \frac{\lambda_I N_I^{eq} + \gamma_{Xe}\Sigma_f\Phi}{\lambda_{Xe}+\sigma_a^{Xe}\Phi}") +
            "<p>The check compares your simulation against this exact formula — if they match, your equations are right.</p>"),
            code=CELLS["ba07ab1f"]),
        Step("s3-predict", "Make a prediction", "predict", (
            "<h1>🛑 STOP. Make a prediction.</h1>"
            "<p>The reactor has been running for days. I-135 and Xe-135 are both at equilibrium. Now the operator "
            "hits <b>SCRAM</b> — the reactor shuts down and the neutron flux instantly drops to <b>zero</b>.</p>"
            "<h3>What happens to the Xe-135 concentration?</h3>"
            "<p>Write your team's guess down, lock it in, <i>then</i> run the next steps and find out who's right.</p>"),
            options=[("A", "It immediately starts falling — no more fission to make it."),
                     ("B", "It stays flat for a while."),
                     ("C", "It rises for several hours before it falls.")], correct="C"),
        Step("s3-scram", "Shut the reactor down", "code", (
            "<h1>TODO-HARD-3 · SCRAM</h1>"
            "<p>Change <b>one number</b>: tell the simulation to trip the reactor after 3 days of operation.</p>"
            + your_turn("Change <code>np.inf</code> (never) to <code>3 * DAY</code>.")),
            hints=["<code>np.inf</code> means “infinitely far in the future” — the reactor never trips.",
                   "<code>shutdown_time = 3 * DAY</code>"],
            after=ac_shutdown, **todo("489abcde")),
        Step("s3-reveal", "THE REVEAL", "sim", (
            "<h1>▶️ THE REVEAL</h1>"
            "<p>Simulate through shutdown and look at what xenon does. Needs the previous steps (equations, equilibrium, "
            "<code>shutdown_time</code>).</p>"
            + callout("Why?", "At shutdown the neutron-absorption term (σ·Φ·N<sub>Xe</sub>) <b>vanishes</b> — nothing "
                      "eats the xenon anymore — but I-135 keeps decaying into it for hours. Xe builds up.", "tip")),
            code=CELLS["d6bf5ea1"], done_if=reveal_done, note=reveal_note),
        Step("s3-dead", "Why it matters: dead-time", "info", (
            "<h1>Why this matters: operator dead-time</h1>"
            "<p>That xenon spike is a giant <b>neutron sponge</b>. For hours after shutdown it can absorb so many "
            "neutrons that the reactor <b>cannot be restarted</b> until the xenon decays away — a window called "
            "<b>dead-time</b> (or “xenon-precluded start-up”). An operator who can't ride through it must wait the "
            "better part of a day.</p>"
            "<p>This is real: a misjudged xenon transient was a contributing factor at <b>Chernobyl</b>.</p>"
            + callout("In this model", "After a 3-day run and a SCRAM, Xe-135 peaks at about <b>1.9×</b> its operating level "
                      "(LWR, ~8 h) and <b>3.4×</b> (CANDU, ~10 h). It takes roughly <b>26 h</b> (LWR) and <b>38 h</b> (CANDU) "
                      "before it falls back to the operating level — so “the better part of a day” is, if anything, "
                      "conservative.", "think")
            + callout("CANDU's answer", "<b>CANDU reactors carry “adjuster rods” specifically to override xenon</b> "
                      "and preserve restart capability — which leads us to the comparison on the next page.", "tip"))),
        Step("s3-compare", "CANDU vs LWR", "sim", (
            "<h1>▶️ CANDU vs LWR</h1>"
            "<p>Why does CANDU care more about xenon? We run both reactors through the same shutdown and plot Xe-135 "
            "<b>normalized to its own operating level</b>, so the <i>shapes</i> line up.</p>"
            + callout("The story", "CANDU's higher flux burns xenon harder while running — so when that burnout suddenly "
                      "stops, the rebound is bigger.", "tip")),
            code=CELLS["f0f1bcf6"]),
        Step("s3-flux", "Play: turn the flux knob", "slider", (
            "<h1>🎚️ Play: turn the flux knob</h1>"
            "<p>Slide the flux from low to high (CANDU). Watch the peak grow. Below a certain flux the peak shrinks "
            "toward nothing — there's not enough burnout to rebound from.</p>"
            "<p>Presets: <b>LWR</b> (3) and <b>CANDU</b> (7) match the two reactors you just compared.</p>"
            + callout("Needs", "your equations from <b>Build the reactor equations</b>. If the plot shows an error, go back "
                      "and finish that step.", "think")),
            code=func_only("d7802513"), autorun=True,
            slider=dict(func="show_peak_for_flux", label="Neutron flux Φ", unit="×10¹³ n/cm²/s", lo=0.5, hi=12.0,
                        step=0.1, value=7.0, presets=[("Low · 1", 1.0), ("LWR · 3", 3.0), ("CANDU · 7", 7.0), ("High · 12", 12.0)])),
    ])
    P.append(s3)

    # ================================================================== 4  DECAY HEAT
    s4 = Section("s4", "Shutdown Decay Heat", "Rung 4", "core2", 0.55, [
        Step("s4-idea", "Why is it still hot?", "info", (
            "<h1>Shutdown decay heat</h1>"
            "<p><b>Analyst's question:</b> the chain reaction stopped. So why is the core still dangerously hot?</p>"
            "<p>Because all those fission products you've been tracking are <b>radioactive</b>, and their decays dump "
            "energy (β and γ) into the fuel. This <b>decay heat</b> can't be switched off. Immediately after shutdown "
            "it's about <b>7% of full power</b> — for a 3000 MW reactor that's ~200 MW with the reactor “off.”</p>"
            "<p>A simple, classic estimate is the <b>Way–Wigner correlation</b> (fuel run for time t<sub>op</sub>):</p>"
            + eq(r"\frac{P(t)}{P_0} \approx 0.066\left[\,t^{-0.2} - (t+t_{op})^{-0.2}\right]") +
            "<p style='color:#6B6B6B'>(t in seconds)</p>")),
        Step("s4-code", "Implement Way–Wigner", "code", (
            "<h1>TODO-EXT-A · Way–Wigner</h1>"
            "<p>One line. (This is a great one for teams who finished Rung 3 early.)</p>"
            "<p><code>T_op</code> is how long the fuel had been running before shutdown (10<sup>7</sup> s ≈ 115 days). "
            "Use <code>**</code> for powers: <code>t**(-0.2)</code>.</p>"
            + your_turn("Replace <code>return None</code> with the formula.")),
            hints=["Two power-law terms, subtracted, times 0.066.",
                   "<code>return 0.066 * (t**(-0.2) - (t + T_op)**(-0.2))</code>"],
            **todo("d9e5e4eb")),
        Step("s4-report", "The analyst's report", "sim", (
            "<h1>▶️ The analyst's report</h1>"
            "<p>Decay heat at 1 hr / 1 day / 1 week.</p>"
            + callout("The takeaway", "At 1 hour you're still removing ~30 MW. <b>This is why you can never stop the cooling</b> — "
                      "loss of cooling on this residual heat is the core of Three Mile Island and Fukushima.", "tip")),
            code=CELLS["cbbd37a1"]),
    ])
    P.append(s4)

    # ================================================================== 5  WASTE
    s5 = Section("s5", "Long-Lived Waste: Cs-137 & Sr-90", "Rung 5", "", 0.5, [
        Step("s5-idea", "How long must we isolate it?", "info", (
            "<h1>Long-lived waste: Cs-137 &amp; Sr-90</h1>"
            "<p><i>Rung 5 — optional extension.</i></p>"
            "<p><b>Analyst's question:</b> once the fuel is removed, how long must we isolate it?</p>"
            "<p>Two fission products dominate the first few centuries of waste heat and radiotoxicity: <b>Cs-137</b> "
            "(t<sub>½</sub> ≈ 30.2 yr) and <b>Sr-90</b> (t<sub>½</sub> ≈ 28.8 yr). A useful rule of thumb: after "
            "<b>~10 half-lives</b> an isotope's activity has fallen by 2<sup>10</sup> ≈ 1000×. For these two, "
            "10 half-lives ≈ <b>~300 years</b> — which is why intermediate waste isolation is quoted on that timescale.</p>"
            + callout("Not the whole story", "Long-lived <i>actinides</i> push the deep-geological requirement to tens of "
                      "thousands of years — a separate problem.", "think"))),
        Step("s5-code", "Decay of the waste inventory", "code", (
            "<h1>TODO-EXT-B · waste decay</h1>"
            "<p>You already know this pattern — it's just single-isotope decay (EASY-2) reused. Fill in the two decay rates.</p>"
            + your_turn("Each isotope simply decays — no parent feeding it here.")),
            hints=["Same as the very first rate equation: minus lambda times N.",
                   "<code>dN_Cs_dt = -lambda_Cs * N_Cs</code> and <code>dN_Sr_dt = -lambda_Sr * N_Sr</code>"],
            after=ac_waste, **todo("ee4b8746")),
        Step("s5-sim", "500 years of isolation", "sim", (
            "<h1>▶️ 500 years of isolation</h1>"
            "<p>Decay the waste inventory over five centuries.</p>"
            + callout("Why ~300 years?", "Cs-137 and Sr-90 fall to ~0.1% after ~10 half-lives. This window drives interim "
                      "spent-fuel storage design. Actinides (e.g. plutonium) decay far slower — that's the case for deep "
                      "geological repositories.", "tip")),
            code=CELLS["92fe7c99"]),
    ])
    P.append(s5)

    # ================================================================== FINISH
    fin = Section("finish", "Wrap-up", "", "people", 0.45, [
        Step("final", "What you built today", "final", (
            "<h1>🎓 What you built today</h1>"
            "<p>As a safety analyst you can now, from first principles:</p>"
            "<ul>"
            "<li>turn a half-life into a rate equation and solve it numerically;</li>"
            "<li>couple isotopes into a decay chain (the Bateman pattern);</li>"
            "<li>model the <b>I-135 → Xe-135</b> reactor system and explain the <b>post-shutdown xenon peak</b> and the "
            "<b>operator dead-time</b> it causes — and why CANDU's high flux makes it worse;</li>"
            "<li>quantify <b>decay heat</b> and argue why core cooling can never be switched off;</li>"
            "<li>estimate the <b>~300-year</b> isolation timescale for the dominant fission products.</li></ul>"
            "<p>Every one of those is a line of physics you wrote yourself. Nicely done. ☢️</p>")),
    ])
    P.append(fin)

    # ---- numbering / lookup
    n = 0
    for i, sec in enumerate(P):
        for j, st in enumerate(sec.steps, start=1):
            st.section = sec.id
            st.label = f"{i}.{j}" if i and sec.id != "finish" else ""
    return P


SECTIONS = build()
ALL_STEPS = [st for sec in SECTIONS for st in sec.steps]
STEP_BY_ID = {st.id: st for st in ALL_STEPS}
