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