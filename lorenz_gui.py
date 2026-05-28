
"""
Lorenz attractor GUI — uses lorenz() from lorenz63.py
Requires: numpy, scipy, matplotlib
Run: python lorenz_gui.py
"""
 
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.widgets import Slider, Button
from lorenz63 import lorenz
 
 
# ── default parameters ──────────────────────────────────────────────────────
DEFAULT = dict(rho=28.0, beta=8/3, sigma=10.0, eps=0.5, T=30.0, dt=0.005)
 
 
def run(rho, beta, sigma, eps, T, dt):
    t = np.arange(0, T, dt)
    ic1 = [1.0, 1.0, 1.0]
    ic2 = [1.0 + eps, 1.0, 1.0]
    params = [rho, beta, sigma]
    s1 = lorenz(t, ic1, params)   # (N, 3)
    s2 = lorenz(t, ic2, params)
    return t, s1, s2
 
 
# ── build figure ─────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(13, 8))
fig.patch.set_facecolor('#f9f8f5')
 
gs = gridspec.GridSpec(
    2, 2,
    left=0.07, right=0.72,
    top=0.93, bottom=0.12,
    hspace=0.35, wspace=0.32,
)
 
ax_xz  = fig.add_subplot(gs[0, 0], projection='3d')   # 3-D attractor
ax_xy  = fig.add_subplot(gs[0, 1])                     # XY projection
ax_t   = fig.add_subplot(gs[1, :])                     # x(t) divergence
 
for ax in [ax_xy, ax_t]:
    ax.set_facecolor('#f9f8f5')
 
C1, C2 = '#378add', '#d85a30'   # blue / coral
 
# ── slider panel ─────────────────────────────────────────────────────────────
slider_specs = [
    ('ρ  (Rayleigh)', 'rho',   1,  50,  DEFAULT['rho'],   0.5),
    ('β',             'beta',  0.1, 5,  DEFAULT['beta'],  0.1),
    ('σ  (Prandtl)', 'sigma',  1,  20,  DEFAULT['sigma'], 0.5),
    ('ε  (IC perturb)', 'eps', 0,   3,  DEFAULT['eps'],   0.05),
    ('T  (duration)', 'T',     5, 100,  DEFAULT['T'],     1.0),
]
 
sliders = {}
slider_left = 0.76
slider_width = 0.20
slider_height = 0.03
slider_gap = 0.08
slider_top = 0.82
 
for i, (label, key, vmin, vmax, vinit, vstep) in enumerate(slider_specs):
    ax_sl = fig.add_axes([slider_left, slider_top - i * slider_gap,
                          slider_width, slider_height])
    sl = Slider(ax_sl, label, vmin, vmax, valinit=vinit, valstep=vstep,
                color='#b5d4f4', track_color='#e6f1fb')
    sl.label.set_fontsize(9)
    sl.valtext.set_fontsize(9)
    sliders[key] = sl
 
ax_reset = fig.add_axes([slider_left + 0.04, 0.04, 0.10, 0.04])
btn_reset = Button(ax_reset, 'Reset', color='#e6f1fb', hovercolor='#b5d4f4')
 
 
# ── draw helpers ─────────────────────────────────────────────────────────────
lines = {}   # keyed by (ax_name, traj_idx)
 
def clear_and_draw(rho, beta, sigma, eps, T, dt=DEFAULT['dt']):
    t, s1, s2 = run(rho, beta, sigma, eps, T, dt)
    x1, y1, z1 = s1[:, 0], s1[:, 1], s1[:, 2]
    x2, y2, z2 = s2[:, 0], s2[:, 1], s2[:, 2]
 
    # ── 3-D attractor ────────────────────────────────────────────────────────
    ax_xz.cla()
    ax_xz.set_facecolor('#f9f8f5')
    ax_xz.plot(x1, y1, z1, lw=0.6, color=C1, alpha=0.7, label='IC₁')
    ax_xz.plot(x2, y2, z2, lw=0.6, color=C2, alpha=0.7, label=f'IC₁ + ε')
    ax_xz.set_xlabel('x', fontsize=8, labelpad=1)
    ax_xz.set_ylabel('y', fontsize=8, labelpad=1)
    ax_xz.set_zlabel('z', fontsize=8, labelpad=1)
    ax_xz.tick_params(labelsize=7)
    ax_xz.set_title('Lorenz attractor (3-D)', fontsize=9, pad=4)
    ax_xz.legend(fontsize=8, loc='upper left')
 
    # ── XZ phase plane ───────────────────────────────────────────────────────
    ax_xy.cla()
    ax_xy.set_facecolor('#f9f8f5')
    ax_xy.plot(x1, z1, lw=0.6, color=C1, alpha=0.8)
    ax_xy.plot(x2, z2, lw=0.6, color=C2, alpha=0.8)
    ax_xy.set_xlabel('x', fontsize=9)
    ax_xy.set_ylabel('z', fontsize=9)
    ax_xy.set_title('XZ projection', fontsize=9)
    ax_xy.tick_params(labelsize=8)
 
    # ── x(t) divergence ──────────────────────────────────────────────────────
    ax_t.cla()
    ax_t.set_facecolor('#f9f8f5')
    ax_t.plot(t, x1, lw=1.0, color=C1, alpha=0.9, label='IC₁')
    ax_t.plot(t, x2, lw=1.0, color=C2, alpha=0.9, label=f'IC₁ + ε={eps:.2f}')
    # divergence envelope
    diff = np.abs(x1 - x2)
    ax_t.fill_between(t, x1 - diff, x1 + diff, alpha=0.08, color=C2)
    ax_t.set_xlabel('t', fontsize=9)
    ax_t.set_ylabel('x(t)', fontsize=9)
    ax_t.set_title('Trajectory divergence — sensitivity to initial conditions', fontsize=9)
    ax_t.legend(fontsize=8, loc='upper right')
    ax_t.tick_params(labelsize=8)
 
    fig.canvas.draw_idle()
 
 
def update(_):
    clear_and_draw(
        rho=sliders['rho'].val,
        beta=sliders['beta'].val,
        sigma=sliders['sigma'].val,
        eps=sliders['eps'].val,
        T=sliders['T'].val,
    )
 
def reset(_):
    for key, sl in sliders.items():
        sl.set_val(DEFAULT[key])
 
 
for sl in sliders.values():
    sl.on_changed(update)
btn_reset.on_clicked(reset)
 
# ── initial draw ─────────────────────────────────────────────────────────────
clear_and_draw(**{k: DEFAULT[k] for k in ['rho', 'beta', 'sigma', 'eps', 'T']})
 
fig.suptitle(
    'Lorenz 63  —  drag sliders to explore chaos & sensitivity to initial conditions',
    fontsize=10, y=0.97, color='#2c2c2a'
)
 
plt.show()