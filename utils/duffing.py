import numpy as np
from scipy.integrate import solve_ivp

def generate_duffing_data(
    z0=(1.0, 0.0),
    delta=0.5,
    t0=0.0,
    t1=3.0,
    dt=0.25,
    method="RK45",
    rtol=1e-9,
    atol=1e-12,
):
    """
    Generate trajectories of the unforced Duffing oscillator:

        x'' + delta*x' - x + x^3 = 0

    Parameters
    ----------
    z0 : array-like, shape (2,) or (n_traj, 2)
        Initial condition(s) ``[x0, v0]``. If a single pair is provided,
        the function returns the same output shapes as before. If multiple
        pairs are provided, trajectories are returned for each initial state.

    Returns:
        t : (N,) time array
        X : (N, 2) for one trajectory, or (n_traj, N, 2) for many
        x : (N,) for one trajectory, or (n_traj, N) for many
        v : (N,) for one trajectory, or (n_traj, N) for many
    """
    def duffing(t, z):
        x, v = z
        return [v, -delta * v + x - x**3]

    # linspace avoids arange's floating-point drift
    N = int(round((t1 - t0) / dt)) + 1
    t_eval = np.linspace(t0, t1, N)

    z0_arr = np.asarray(z0, dtype=float)
    if z0_arr.ndim == 1:
        if z0_arr.shape[0] != 2:
            raise ValueError("z0 must have shape (2,) or (n_traj, 2).")
        z0_all = z0_arr.reshape(1, 2)
        single = True
    elif z0_arr.ndim == 2 and z0_arr.shape[1] == 2:
        z0_all = z0_arr
        single = False
    else:
        raise ValueError("z0 must have shape (2,) or (n_traj, 2).")

    X_all = []
    x_all = []
    v_all = []
    t_ref = None

    for z0_i in z0_all:
        sol = solve_ivp(
            duffing,
            (t0, t1),
            z0_i.tolist(),
            t_eval=t_eval,
            method=method,
            rtol=rtol,
            atol=atol,
            dense_output=False,
        )

        if not sol.success:
            raise RuntimeError(f"solve_ivp failed: {sol.message}")

        if t_ref is None:
            t_ref = sol.t

        x_i = sol.y[0]
        v_i = sol.y[1]
        X_i = np.column_stack([x_i, v_i])

        x_all.append(x_i)
        v_all.append(v_i)
        X_all.append(X_i)

    t = t_ref
    X_stack = np.stack(X_all, axis=0)
    x_stack = np.stack(x_all, axis=0)
    v_stack = np.stack(v_all, axis=0)

    if single:
        return t, X_stack[0], x_stack[0], v_stack[0]
    return t, X_stack, x_stack, v_stack