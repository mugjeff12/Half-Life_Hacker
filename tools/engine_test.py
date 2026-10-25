"""Headless end-to-end test of the lesson engine: run every step with its solution, in order."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import numpy as np
from hlh.session import Session
from hlh.content import ALL_STEPS


def run_all(verbose=True):
    s = Session()
    failures = []
    for st in ALL_STEPS:
        if st.kind in ("info", "final"):
            continue
        if st.kind == "predict":
            continue
        code = st.solution or st.code
        r = s.run(code, f"<{st.id}>", after=st.after)
        passed = r.ok and (r.checks_ok if r.checks else True)
        if passed and st.done_if:
            passed = bool(st.done_if(s.ns))
        if st.kind == "slider":
            r2 = s.call(st.slider["func"], st.slider["value"])
            passed = r.ok and r2.ok and len(r2.figures) == 1
            if not r2.ok: print("   slider err:", r2.error)
        n = len(r.figures)
        if verbose:
            print(f"{'PASS' if passed else 'FAIL'}  {st.label:>4} {st.id:12} figs={n} checks={[c[1] for c in r.checks]}")
        if not passed:
            failures.append(st.id); print(r.error, r.output[-400:])
    return s, failures


if __name__ == "__main__":
    s, f = run_all()
    ns = s.ns
    print("\nFailures:", f)
    print(f"CANDU: overshoot {ns['overshoot']:.2f}x at {ns['t_peak']-ns['sd_h']:.1f} h after shutdown")
    import hlh.physics_ref as ref
    from scipy.integrate import solve_ivp
    for name, R in (("LWR", ref.LWR), ("CANDU", ref.CANDU)):
        sol = ns['simulate_xenon'](R, 3*ns['DAY'], 7)
        Phi, Sig = R['Phi'], R['Sigma_f']
        NIeq = ref.gamma_I*Sig*Phi/ref.lambda_I; NXe = (ref.lambda_I*NIeq+ref.gamma_Xe*Sig*Phi)/(ref.lambda_Xe+ref.sigma_a_Xe*Phi)
        post = sol.t >= 3*ns['DAY']; nrm = sol.y[1][post]/NXe; tt = (sol.t[post]-3*ns['DAY'])/3600
        pk = nrm.argmax()
        back = tt[(tt > tt[pk]) & (nrm < 1.0)]
        print(f"{name}: peak {nrm[pk]:.2f}x at {tt[pk]:.1f} h; back below operating level at {back[0] if len(back) else float('nan'):.1f} h")
    # flux sweep
    for phi in (0.5, 1, 2, 3, 7, 12):
        sol = ns['solve_ivp'](ns['xenon_system'], [0, 7*ns['DAY']], [0, 0], args=(ref.CANDU['Sigma_f'], ns['make_flux'](phi*1e13, 3*ns['DAY'])),
                              method="Radau", t_eval=np.linspace(0, 7*ns['DAY'], 3000), max_step=1800., rtol=1e-8, atol=1e6)
        NIeq = ref.gamma_I*ref.CANDU['Sigma_f']*phi*1e13/ref.lambda_I; NXe = (ref.lambda_I*NIeq+ref.gamma_Xe*ref.CANDU['Sigma_f']*phi*1e13)/(ref.lambda_Xe+ref.sigma_a_Xe*phi*1e13)
        print(f"flux {phi:>4}e13 -> peak {sol.y[1].max()/NXe:.2f}x")
    import time; t0=time.time(); s.call('show_peak_for_flux', 7.0); print("slider render time %.2fs" % (time.time()-t0))
    sys.exit(1 if f else 0)
