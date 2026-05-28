"""Koopman operator estimation utilities.

This module provides a scikit-learn style estimator that learns a finite
dimensional approximation of the Koopman operator from state snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations_with_replacement
from typing import Literal

import numpy as np

try:
	from sklearn.base import BaseEstimator, RegressorMixin
except ImportError:
	# Lightweight fallback so the class remains usable without scikit-learn.
	class BaseEstimator:  # type: ignore[override]
		"""Fallback base estimator."""

	class RegressorMixin:  # type: ignore[override]
		"""Fallback regressor mixin."""


ObservableType = Literal["linear", "polynomial", "rbf", "rff"]



class KoopmanEstimator(BaseEstimator, RegressorMixin):
	"""Estimate a Koopman operator from state transition data.

	Parameters
	----------
	observable_type:
		Type of lifting map. One of ``"linear"``, ``"polynomial"``, ``"rbf"``,
		or ``"rff"``.
	degree:
		Maximum total degree for polynomial observables.
	n_centers:
		Number of RBF centers used when ``observable_type='rbf'``.
	n_fourier_features:
		Number of random Fourier frequencies used when
		``observable_type='rff'``. The lifted dimension contributed by the
		Fourier block is ``2 * n_fourier_features``.
	gamma:
		Kernel bandwidth parameter. For ``'rbf'`` it gives
		``exp(-gamma ||x-c||^2)``. For ``'rff'`` it parameterizes the
		approximated RBF kernel ``exp(-gamma ||x-y||^2)``. If ``None``, uses
		``1 / state_dimension``.
	include_bias:
		Whether to include a constant observable.
	include_state:
		Whether to append raw state coordinates in polynomial/RBF observables.
	random_state:
		Optional seed for reproducible RBF center selection.
	reg:
		Optional Tikhonov regularization strength used in least squares.
	"""

	def __init__(
		self,
		observable_type: ObservableType = "linear",
		degree: int = 2,
		n_centers: int = 50,
		n_fourier_features: int = 100,
		gamma: float | None = None,
		include_bias: bool = True,
		include_state: bool = True,
		random_state: int | None = None,
		reg: float = 0.0,
	) -> None:
		self.observable_type = observable_type
		self.degree = degree
		self.n_centers = n_centers
		self.n_fourier_features = n_fourier_features
		self.gamma = gamma
		self.include_bias = include_bias
		self.include_state = include_state
		self.random_state = random_state
		self.reg = reg

	def fit(
		self,
		X: np.ndarray,
		Y: np.ndarray | None = None,
	) -> "KoopmanEstimator":
		"""Fit Koopman operator from snapshots.

		If ``Y`` is not provided, consecutive snapshot pairs are inferred from
		``X`` such that ``(X[:-1], X[1:])`` are used for training.
		"""
		X = self._as_2d(X)
		if Y is None:
			if X.shape[0] < 2:
				raise ValueError("X must contain at least 2 samples when Y is None.")
			X_train = X[:-1]
			Y_train = X[1:]
		else:
			Y = self._as_2d(Y)
			if X.shape != Y.shape:
				raise ValueError("X and Y must have the same shape.")
			X_train = X
			Y_train = Y

		if self.observable_type not in {"linear", "polynomial", "rbf", "rff"}:
			raise ValueError(
				"observable_type must be one of: 'linear', 'polynomial', 'rbf', 'rff'."
			)
		if self.degree < 1:
			raise ValueError("degree must be >= 1.")
		if self.n_centers < 1:
			raise ValueError("n_centers must be >= 1.")
		if self.n_fourier_features < 1:
			raise ValueError("n_fourier_features must be >= 1.")
		if not self.include_bias and self.observable_type in {"linear", "polynomial"} and not self.include_state:
			raise ValueError(
				"At least one observable must be active. Enable include_bias or include_state."
			)

		self.n_features_in_ = X_train.shape[1]
		self._rng = np.random.default_rng(self.random_state)
		self._fit_observables(X_train)

		psi_x = self._lift(X_train)
		psi_y = self._lift(Y_train)

		# Solve psi_x @ K ~= psi_y in least-squares form.
		self.K_ = self._solve_least_squares(psi_x, psi_y)

		# Learn decoder mapping observables back to state space.
		self.B_ = self._solve_least_squares(psi_x, X_train)

		self.n_observables_ = self.K_.shape[0]
		self.is_fitted_ = True
		return self

	def predict(self, X: np.ndarray, steps: int = 1) -> np.ndarray:
		"""Predict future states.

		Parameters
		----------
		X:
			Initial state(s), shape ``(n_samples, n_states)`` or ``(n_states,)``.
		steps:
			Number of forward steps. For ``steps=1``, output has shape
			``(n_samples, n_states)``. For ``steps>1``, output shape is
			``(n_samples, steps, n_states)``.
		"""
		self._check_is_fitted()
		if steps < 1:
			raise ValueError("steps must be >= 1.")

		X = self._as_2d(X)
		self._validate_state_dim(X)
		psi = self._lift(X)

		if steps == 1:
			psi_next = psi @ self.K_
			return psi_next @ self.B_

		rollout = np.empty((X.shape[0], steps, self.n_features_in_), dtype=float)
		psi_k = psi.copy()
		for k in range(steps):
			psi_k = psi_k @ self.K_
			rollout[:, k, :] = psi_k @ self.B_
		return rollout

	def reconstruct(self, X0: np.ndarray, n_steps: int) -> np.ndarray:
		"""Reconstruct trajectory from initial condition(s).

		Returns a trajectory including the initial condition, with shape
		``(n_steps + 1, n_states)`` for a single input state and
		``(n_samples, n_steps + 1, n_states)`` for batch input.
		"""
		self._check_is_fitted()
		if n_steps < 1:
			raise ValueError("n_steps must be >= 1.")

		X0_array = np.asarray(X0, dtype=float)
		single = X0_array.ndim == 1
		X0_2d = self._as_2d(X0_array)
		self._validate_state_dim(X0_2d)

		traj = np.empty((X0_2d.shape[0], n_steps + 1, self.n_features_in_), dtype=float)
		traj[:, 0, :] = X0_2d
		traj[:, 1:, :] = self.predict(X0_2d, steps=n_steps)

		if single:
			return traj[0]
		return traj

	def _fit_observables(self, X: np.ndarray) -> None:
		"""Learn parameters used by the chosen lifting map."""
		n_states = X.shape[1]

		if self.observable_type == "polynomial":
			self._poly_combinations_ = []
			for deg in range(2, self.degree + 1):
				self._poly_combinations_.extend(
					list(combinations_with_replacement(range(n_states), deg))
				)

		if self.observable_type == "rbf":
			n_centers = min(self.n_centers, X.shape[0])
			indices = self._rng.choice(X.shape[0], size=n_centers, replace=False)
			self.rbf_centers_ = X[indices]
			self.rbf_gamma_ = (1.0 / n_states) if self.gamma is None else float(self.gamma)

		if self.observable_type == "rff":
			self.rff_gamma_ = (1.0 / n_states) if self.gamma is None else float(self.gamma)
			self.rff_weights_ = self._rng.normal(
				loc=0.0,
				scale=np.sqrt(2.0 * self.rff_gamma_),
				size=(n_states, self.n_fourier_features),
			)

	def _lift(self, X: np.ndarray) -> np.ndarray:
		"""Map states into observable space."""
		X = self._as_2d(X)
		parts = []

		if self.include_bias:
			parts.append(np.ones((X.shape[0], 1), dtype=float))

		if self.observable_type == "linear":
			if self.include_state:
				parts.append(X)

		elif self.observable_type == "polynomial":
			if self.include_state:
				parts.append(X)
			for combo in self._poly_combinations_:
				monomial = np.prod(X[:, combo], axis=1, keepdims=True)
				parts.append(monomial)

		elif self.observable_type == "rbf":
			if self.include_state:
				parts.append(X)
			# Pairwise squared Euclidean distances to RBF centers.
			diffs = X[:, None, :] - self.rbf_centers_[None, :, :]
			sq_dist = np.sum(diffs * diffs, axis=2)
			parts.append(np.exp(-self.rbf_gamma_ * sq_dist))

		elif self.observable_type == "rff":
			if self.include_state:
				parts.append(X)
			projection = X @ self.rff_weights_
			scale = np.sqrt(1.0 / self.n_fourier_features)
			parts.append(
				scale * np.hstack([np.cos(projection), np.sin(projection)])
			)

		else:
			raise RuntimeError("Unsupported observable type during lifting.")

		if not parts:
			raise ValueError(
				"Observable lift produced no features. Enable include_bias/include_state or choose a richer observable_type."
			)

		return np.hstack(parts)

	def _solve_least_squares(self, A: np.ndarray, B: np.ndarray) -> np.ndarray:
		"""Solve min_X ||AX-B|| with optional ridge regularization."""
		if self.reg > 0:
			gram = A.T @ A
			rhs = A.T @ B
			reg_eye = self.reg * np.eye(gram.shape[0], dtype=gram.dtype)
			return np.linalg.solve(gram + reg_eye, rhs)
		return np.linalg.lstsq(A, B, rcond=None)[0]

	@staticmethod
	def _as_2d(X: np.ndarray) -> np.ndarray:
		"""Convert input to a 2D float array."""
		X = np.asarray(X, dtype=float)
		if X.ndim == 1:
			return X.reshape(1, -1)
		if X.ndim != 2:
			raise ValueError("Input must be a 1D or 2D array.")
		return X

	def _check_is_fitted(self) -> None:
		if not getattr(self, "is_fitted_", False):
			raise RuntimeError("Estimator is not fitted. Call fit(...) first.")

	def _validate_state_dim(self, X: np.ndarray) -> None:
		if X.shape[1] != self.n_features_in_:
			raise ValueError(
				f"Expected input with {self.n_features_in_} state dimensions, got {X.shape[1]}."
			)

