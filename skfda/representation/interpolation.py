"""
Module to interpolate functional data objects.
"""


from scipy.interpolate import (PchipInterpolator, UnivariateSpline,
                               RectBivariateSpline, RegularGridInterpolator)

import numpy as np

from .evaluator import Evaluator, EvaluatorConstructor


# Scipy interpolator methods used internally
class SplineInterpolator(EvaluatorConstructor):
    r"""Spline interpolator of :class:`FDataGrid`.

    Spline interpolator of discretized functional objects. Implements different
    interpolation methods based in splines, using the sample points of the
    grid as nodes to interpolate.

    See the interpolation example to a detailled explanation.

    Attributes:
        interpolator_order (int, optional): Order of the interpolation, 1
            for linear interpolation, 2 for cuadratic, 3 for cubic and so
            on. In case of curves and surfaces there is available
            interpolation up to degree 5. For higher dimensional objects
            only linear or nearest interpolation is available. Default
            lineal interpolation.
        smoothness_parameter (float, optional): Penalisation to perform
            smoothness interpolation. Option only available for curves and
            surfaces. If 0 the residuals of the interpolation will be 0.
            Defaults 0.
        monotone (boolean, optional): Performs monotone interpolation in
            curves using a PCHIP interpolator. Only valid for curves (domain
            dimension equal to 1) and interpolation order equal to 1 or 3.
            Defaults false.

    """

    def __init__(self, interpolation_order=1, smoothness_parameter=0.,
                 monotone=False):
        r"""Constructor of the SplineInterpolator.

        Args:
            interpolator_order (int, optional): Order of the interpolation, 1
                for linear interpolation, 2 for cuadratic, 3 for cubic and so
                on. In case of curves and surfaces there is available
                interpolation up to degree 5. For higher dimensional objects
                only linear or nearest interpolation is available. Default
                lineal interpolation.
            smoothness_parameter (float, optional): Penalisation to perform
                smoothness interpolation. Option only available for curves and
                surfaces. If 0 the residuals of the interpolation will be 0.
                Defaults 0.
            monotone (boolean, optional): Performs monotone interpolation in
                curves using a PCHIP interpolator. Only valid for curves
                (domain dimension equal to 1) and interpolation order equal
                to 1 or 3.
                Defaults false.

        """
        self._interpolation_order = interpolation_order
        self._smoothness_parameter = smoothness_parameter
        self._monotone = monotone

    @property
    def interpolation_order(self):
        "Returns the interpolation order"
        return self._interpolation_order

    @property
    def smoothness_parameter(self):
        "Returns the smoothness parameter"
        return self._smoothness_parameter

    @property
    def monotone(self):
        "Returns flag to perform monotone interpolation"
        return self._monotone

    def __eq__(self, other):
        """Equality operator between SplineInterpolator"""
        return (super().__eq__(other) and
                self.interpolation_order == other.interpolation_order and
                self.smoothness_parameter == other.smoothness_parameter and
                self.monotone == other.monotone)

    def evaluator(self, fdatagrid):
        """Construct a SplineInterpolatorEvaluator used in the evaluation.

        Args:
            fdatagrid (:class:`FDataGrid`): Functional object where the
                evaluator will be used.

        Returns:
            (:class:`SplineInterpolatorEvaluator`): Evaluator of the fdatagrid.

        """
        return SplineInterpolatorEvaluator(fdatagrid, self.interpolation_order,
                                           self.smoothness_parameter,
                                           self.monotone)

    def __repr__(self):
        """repr method of the interpolator"""
        return (f"{type(self).__name__}("
                f"interpolation_order={self.interpolation_order}, "
                f"smoothness_parameter={self.smoothness_parameter}, "
                f"monotone={self.monotone})")


class SplineInterpolatorEvaluator(Evaluator):
    r"""Spline interpolator evaluator of :class:`FDataGrid`.

    It is generated by the SplineInterpolator, and it is used internally
    during the evaluation.

    Spline interpolator of discretized functional objects. Implements different
    interpolation methods based in splines, using the sample points of the
    grid as nodes to interpolate.

    See the interpolation example to a detailled explanation.

    Attributes:
        interpolator_order (int, optional): Order of the interpolation, 1
            for linear interpolation, 2 for cuadratic, 3 for cubic and so
            on. In case of curves and surfaces there is available
            interpolation up to degree 5. For higher dimensional objects
            only linear or nearest interpolation is available. Default
            lineal interpolation.
        smoothness_parameter (float, optional): Penalisation to perform
            smoothness interpolation. Option only available for curves and
            surfaces. If 0 the residuals of the interpolation will be 0.
            Defaults 0.
        monotone (boolean, optional): Performs monotone interpolation in
            curves using a PCHIP interpolator. Only valid for curves (domain
            dimension equal to 1) and interpolation order equal to 1 or 3.
            Defaults false.

    """

    def __init__(self, fdatagrid, k=1, s=0., monotone=False):
        r"""Constructor of the SplineInterpolatorEvaluator.

        Args:
            fdatagir (fdatagrid): Grid to be interpolated.
            interpolator_order (int, optional): Order of the interpolation, 1
                for linear interpolation, 2 for cuadratic, 3 for cubic and so
                on. In case of curves and surfaces there is available
                interpolation up to degree 5. For higher dimensional objects
                only linear or nearest interpolation is available. Default
                lineal interpolation.
            smoothness_parameter (float, optional): Penalisation to perform
                smoothness interpolation. Option only available for curves and
                surfaces. If 0 the residuals of the interpolation will be 0.
                Defaults 0.
            monotone (boolean, optional): Performs monotone interpolation in
                curves using a PCHIP interpolator. Only valid for curves
                (domain dimension equal to 1) and interpolation order equal to
                1 or 3.
                Defaults false.

        """
        sample_points = fdatagrid.sample_points
        data_matrix = fdatagrid.data_matrix

        self._fdatagrid = fdatagrid
        self._dim_codomain = fdatagrid.dim_codomain
        self._dim_domain = fdatagrid.dim_domain
        self._n_samples = fdatagrid.n_samples
        self._keepdims = fdatagrid.keepdims
        self._domain_range = fdatagrid.domain_range

        if self._dim_domain == 1:
            self._splines = self._construct_spline_1_m(sample_points,
                                                       data_matrix,
                                                       k, s, monotone)
        elif monotone:
            raise ValueError("Monotone interpolation is only supported with "
                             "domain dimension equal to 1.")

        elif self._dim_domain == 2:
            self._splines = self._construct_spline_2_m(sample_points,
                                                       data_matrix, k, s)

        elif s != 0:
            raise ValueError("Smoothing interpolation is only supported with "
                             "domain dimension up to 2, s should be 0.")

        else:
            self._splines = self._construct_spline_n_m(sample_points,
                                                       data_matrix, k)

        # After the creation of the splines the fdatagrid reference can
        # be deleted
        self._fdatagrid = None

    def _construct_spline_1_m(self, sample_points, data_matrix,
                              k, s, monotone):
        r"""Construct the matrix of interpolators for curves.

        Constructs the matrix of interpolators for objects with domain
        dimension = 1. Calling internally during the creationg of the
        evaluator.

        Uses internally the scipy interpolator UnivariateSpline or
        PchipInterpolator.

        Args:
            sample_points (np.ndarray): Sample points of the fdatagrid.
            data_matrix (np.ndarray): Data matrix of the fdatagrid.
            k (integer): Order of the spline interpolators.

        Returns:
            (np.ndarray): Array of size n_samples x dim_codomain with the
            corresponding interpolator of the sample i, and image dimension j
            in the entry (i,j) of the array.

        Raises:
            ValueError: If the value of the interpolation k is not valid.

        """
        if k > 5 or k < 1:
            raise ValueError(f"Invalid degree of interpolation ({k}). Must be "
                             f"an integer greater than 0 and lower or "
                             f"equal than 5.")

        if monotone and s != 0:
            raise ValueError("Smoothing interpolation is not supported with "
                             "monotone interpolation")

        if monotone and (k == 2 or k == 4):
            raise ValueError(f"monotone interpolation of degree {k}"
                             f"not supported.")

        # Monotone interpolation of degree 1 is performed with linear spline
        if monotone and k == 1:
            monotone = False

        # Evaluator of splines called in evaluate

        def _spline_evaluator_1_m(spl, t, der):

            return spl(t, der)

        def _process_derivative_1_m(derivative):

            return derivative

        self._spline_evaluator = _spline_evaluator_1_m

        self._process_derivative = _process_derivative_1_m

        sample_points = sample_points[0]

        if monotone:
            def constructor(data):
                """Constructs an unidimensional cubic monotone interpolator"""
                return PchipInterpolator(sample_points, data)

        else:

            def constructor(data):
                """Constructs an unidimensional interpolator"""
                return UnivariateSpline(sample_points, data, s=s, k=k)

        return np.apply_along_axis(constructor, 1, data_matrix)

    def _construct_spline_2_m(self, sample_points, data_matrix, k, s):
        r"""Construct the matrix of interpolators for surfaces.

        Constructs the matrix of interpolators for objects with domain
        dimension = 2. Calling internally during the creationg of the
        evaluator.

        Uses internally the scipy interpolator RectBivariateSpline.

        Args:
            sample_points (np.ndarray): Sample points of the fdatagrid.
            data_matrix (np.ndarray): Data matrix of the fdatagrid.
            k (integer): Order of the spline interpolators.

        Returns:
            (np.ndarray): Array of size n_samples x dim_codomain with the
            corresponding interpolator of the sample i, and image dimension j
            in the entry (i,j) of the array.

        Raises:
            ValueError: If the value of the interpolation k is not valid.

        """
        if np.isscalar(k):
            kx = ky = k
        elif len(k) != 2:
            raise ValueError("k should be numeric or a tuple of length 2.")
        else:
            kx = k[0]
            ky = k[1]

        if kx > 5 or kx <= 0 or ky > 5 or ky <= 0:
            raise ValueError(f"Invalid degree of interpolation ({kx},{ky}). "
                             f"Must be an integer greater than 0 and lower or "
                             f"equal than 5.")

        def _spline_evaluator_2_m(spl, t, der):

            return spl(t[:, 0], t[:, 1], dx=der[0], dy=der[1], grid=False)

        def _process_derivative_2_m(derivative):
            if np.isscalar(derivative):
                derivative = 2 * [derivative]
            elif len(derivative) != 2:
                raise ValueError("derivative should be a numeric value "
                                 "or a tuple of length 2 with (dx,dy).")

            return derivative

        # Evaluator of splines called in evaluate
        self._spline_evaluator = _spline_evaluator_2_m
        self._process_derivative = _process_derivative_2_m

        # Matrix of splines
        spline = np.empty((self._n_samples, self._dim_codomain), dtype=object)

        for i in range(self._n_samples):
            for j in range(self._dim_codomain):
                spline[i, j] = RectBivariateSpline(sample_points[0],
                                                   sample_points[1],
                                                   data_matrix[i, :, :, j],
                                                   kx=kx, ky=ky, s=s)

        return spline

    def _construct_spline_n_m(self, sample_points, data_matrix, k):
        r"""Construct the matrix of interpolators.

        Constructs the matrix of interpolators for objects with domain
        dimension > 2. Calling internally during the creationg of the
        evaluator.

        Only linear and nearest interpolators are available for objects with
        domain dimension >= 3. Uses internally the scipy interpolator
        RegularGridInterpolator.

        Args:
            sample_points (np.ndarray): Sample points of the fdatagrid.
            data_matrix (np.ndarray): Data matrix of the fdatagrid.
            k (integer): Order of the spline interpolators.

        Returns:
            (np.ndarray): Array of size n_samples x dim_codomain with the
            corresponding interpolator of the sample i, and image dimension j
            in the entry (i,j) of the array.

        Raises:
            ValueError: If the value of the interpolation k is not valid.

        """
        # Parses method of interpolation
        if k == 0:
            method = 'nearest'
        elif k == 1:
            method = 'linear'
        else:
            raise ValueError("interpolation order should be 0 (nearest) or 1 "
                             "(linear).")

        def _process_derivative_n_m(derivative):
            if derivative != 0:
                raise ValueError("derivates not suported for functional data "
                                 " with domain dimension greater than 2.")

            return derivative

        def _spline_evaluator_n_m(spl, t, derivative):

            return spl(t)

        # Method to process derivative argument
        self._process_derivative = _process_derivative_n_m

        # Evaluator of splines called in evaluate
        self._spline_evaluator = _spline_evaluator_n_m

        spline = np.empty((self._n_samples, self._dim_codomain), dtype=object)

        for i in range(self._n_samples):
            for j in range(self._dim_codomain):
                spline[i, j] = RegularGridInterpolator(
                    sample_points, data_matrix[i, ..., j], method, False)

        return spline

    def evaluate(self, eval_points, *, derivative=0):
        r"""Evaluation method.

        Evaluates the samples at different evaluation points. The evaluation
        call will receive a 3-d array with the evaluation points for
        each sample.

        This method is called internally by :meth:`evaluate` when the argument
        `aligned_evaluation` is False.

        Args:
            eval_points (np.ndarray): Numpy array with shape
                `(n_samples, number_eval_points, dim_domain)` with the
                 evaluation points for each sample.
            derivative (int, optional): Order of the derivative. Defaults to 0.

        Returns:
            (np.darray): Numpy 3d array with shape `(n_samples,
                number_eval_points, dim_codomain)` with the result of the
                evaluation. The entry (i,j,k) will contain the value k-th image
                dimension of the i-th sample, at the j-th evaluation point.

        Raises:
            ValueError: In case of an incorrect value of the derivative
                argument.

        """
        derivative = self._process_derivative(derivative)

        # Constructs the evaluator for t_eval
        if self._dim_codomain == 1:
            def evaluator(spl):
                """Evaluator of object with image dimension equal to 1."""
                return self._spline_evaluator(spl[0], eval_points, derivative)
        else:
            def evaluator(spl_m):
                """Evaluator of multimensional object"""
                return np.dstack(
                    [self._spline_evaluator(spl, eval_points, derivative)
                     for spl in spl_m]).flatten()

        # Points evaluated inside the domain
        res = np.apply_along_axis(evaluator, 1, self._splines)
        res = res.reshape(self._n_samples, eval_points.shape[0],
                          self._dim_codomain)

        return res

    def evaluate_composed(self, eval_points, *, derivative=0):
        """Evaluation method.

        Evaluates the samples at different evaluation points. The evaluation
        call will receive a 3-d array with the evaluation points for
        each sample.

        This method is called internally by :meth:`evaluate` when the argument
        `aligned_evaluation` is False.

        Args:
            eval_points (np.ndarray): Numpy array with shape
                `(n_samples, number_eval_points, dim_domain)` with the
                 evaluation points for each sample.
            derivative (int, optional): Order of the derivative. Defaults to 0.

        Returns:
            (np.darray): Numpy 3d array with shape `(n_samples,
                number_eval_points, dim_codomain)` with the result of the
                evaluation. The entry (i,j,k) will contain the value k-th image
                dimension of the i-th sample, at the j-th evaluation point.

        Raises:
            ValueError: In case of an incorrect value of the derivative
                argument.

        """
        shape = (self._n_samples, eval_points.shape[1], self._dim_codomain)
        res = np.empty(shape)

        derivative = self._process_derivative(derivative)

        if self._dim_codomain == 1:
            def evaluator(t, spl):
                """Evaluator of sample with image dimension equal to 1"""
                return self._spline_evaluator(spl[0], t, derivative)

            for i in range(self._n_samples):
                res[i] = evaluator(eval_points[i], self._splines[i]).reshape(
                    (eval_points.shape[1], self._dim_codomain))

        else:
            def evaluator(t, spl_m):
                """Evaluator of multidimensional sample"""
                return np.array([self._spline_evaluator(spl, t, derivative)
                                 for spl in spl_m]).T

            for i in range(self._n_samples):
                res[i] = evaluator(eval_points[i], self._splines[i])

        return res
