import numpy as np
from scipy.integrate import ode

# code borrowed from https://dafi.readthedocs.io/en/latest/tutorial_lorenz.html#
def lorenz(time_series, init_state, parameters):
    # define Lorenz system
    def lorenz63(time, state, parameters):
        xstate, ystate, zstate = state
        rho, beta, sigma = parameters
        ddt_x = sigma * (ystate - xstate)
        ddt_y = rho*xstate - ystate - xstate*zstate
        ddt_z = xstate*ystate - beta*zstate
        return [ddt_x, ddt_y, ddt_z]

    # solve lorenz system
    solver = ode(lorenz63)
    solver.set_integrator('dopri5')
    solver.set_initial_value(init_state, time_series[0])
    solver.set_f_params(parameters)
    state = np.expand_dims(np.array(init_state), axis=0)
    for time in time_series[1:]:
        if not solver.successful():
            raise RuntimeError('Solver failed at time: {} s'.format(time))
        else:
            solver.integrate(time)
        state = np.vstack((state, solver.y))
    return state

def lorenz_variational(time_series, init_state, parameters, t_transient=0):
    """Integrate Lorenz-63 + variational equation simultaneously."""
    rho, beta, sigma = parameters

    def lorenz63_var(time, state_and_phi, parameters):
        rho, beta, sigma = parameters
        x, y, z = state_and_phi[:3]
        Phi = state_and_phi[3:].reshape(3, 3)

        # state equations
        dstate = [sigma*(y-x), rho*x - y - x*z, x*y - beta*z]

        # Jacobian at current state
        J = np.array([
            [-sigma,   sigma,  0    ],
            [rho - z, -1,     -x   ],
            [y,        x,     -beta],
        ])

        # variational equation
        dPhi = (J @ Phi).ravel()
        return np.concatenate([dstate, dPhi])

    # initial condition: state + identity matrix (no perturbation)
    init = np.concatenate([init_state, np.eye(3).ravel()])

    solver = ode(lorenz63_var)
    solver.set_integrator('dopri5', rtol=1e-10, atol=1e-10)
    solver.set_initial_value(init, time_series[0])
    solver.set_f_params(parameters)

    Q = np.eye(3)
    exponents = np.zeros(3)
    states = [np.array(init_state)]

    for time in time_series[1:]:
        if not solver.successful():
            raise RuntimeError(f'Solver failed at time: {time}')
        solver.integrate(time)
        state = solver.y[:3]
        Phi   = solver.y[3:].reshape(3, 3)
        states.append(state.copy())

        # QR decomposition and accumulate
        Phi, R = np.linalg.qr(Phi)
        if time >= t_transient:
            exponents += np.log(np.abs(np.diag(R)))
        else:
            Phi = np.eye(3)  # reset exponents accumulation

        # reset Phi to Q in solver state
        solver.set_initial_value(np.concatenate([state, Phi.ravel()]), time)

    dt = time_series[1] - time_series[0]
    trajectory = np.array(states)
    t_total = (time_series[-1] - t_transient)
    lyapunov_exponents = exponents / t_total
    return trajectory, lyapunov_exponents
