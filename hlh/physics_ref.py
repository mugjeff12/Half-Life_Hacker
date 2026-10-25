"""Reference physics (independent of student code) — used for hidden auto-checks and the self-test."""
import numpy as np

HOUR = 3600.0
DAY = 24 * HOUR
WEEK = 7 * DAY
YEAR = 365.25 * DAY

t_half_I = 6.57 * HOUR
t_half_Xe = 9.17 * HOUR
gamma_I = 0.0628
gamma_Xe = 0.003
sigma_a_Xe = 2.65e6 * 1e-24
lambda_I = np.log(2) / t_half_I
lambda_Xe = np.log(2) / t_half_Xe
lambda_Cs = np.log(2) / (30.17 * YEAR)
lambda_Sr = np.log(2) / (28.79 * YEAR)
CANDU = {"name": "CANDU", "Phi": 7.0e13, "Sigma_f": 0.0054}
LWR = {"name": "LWR (PWR)", "Phi": 3.0e13, "Sigma_f": 0.10}


def xenon_rates(N_I, N_Xe, Sigma_f, Phi):
    dI = gamma_I * Sigma_f * Phi - lambda_I * N_I
    dXe = lambda_I * N_I + gamma_Xe * Sigma_f * Phi - lambda_Xe * N_Xe - sigma_a_Xe * Phi * N_Xe
    return dI, dXe
