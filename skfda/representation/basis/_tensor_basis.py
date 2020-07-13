import itertools

import numpy as np

from ..._utils import _same_domain
from ._basis import Basis


class Tensor(Basis):
    r"""Tensor basis.

    Basis for multivariate functions constructed as a tensor product of 
    :math:`\mathbb{R} \to \mathbb{R}` bases.


    Attributes:
        domain_range (tuple): a tuple of length ``dim_domain`` containing
            the range of input values for each dimension.
        n_basis (int): number of functions in the basis.

    Examples:
        Defines a vector-valued base over the interval :math:`[0, 5]`
        consisting on the functions

        .. math::

            1 \vec{i}, t \vec{i}, t^2 \vec{i}, 1 \vec{j}, t \vec{j}

        >>> from skfda.representation.basis import VectorValued, Monomial
        >>>
        >>> basis_x = Monomial((0,5), n_basis=3)
        >>> basis_y = Monomial((0,5), n_basis=2)
        >>>
        >>> basis = VectorValued([basis_x, basis_y])


        And evaluates all the functions in the basis in a list of descrete
        values.

        >>> basis([0., 1., 2.])
        array([[[ 1.,  0.],
                [ 1.,  0.],
                [ 1.,  0.]],
               [[ 0.,  0.],
                [ 1.,  0.],
                [ 2.,  0.]],
               [[ 0.,  0.],
                [ 1.,  0.],
                [ 4.,  0.]],
               [[ 0.,  1.],
                [ 0.,  1.],
                [ 0.,  1.]],
               [[ 0.,  0.],
                [ 0.,  1.],
                [ 0.,  2.]]])

    """

    def __init__(self, basis_list):

        if not all(b.dim_domain == 1 and b.dim_codomain == 1
                   for b in basis_list):
            raise ValueError("The basis functions must be "
                             "univariate and scalar valued")

        self.basis_list = basis_list

        super().__init__(
            domain_range=[b.domain_range[0] for b in basis_list],
            n_basis=np.prod([b.n_basis for b in basis_list]))

    @property
    def dim_domain(self):
        return len(self.basis_list)

    def _evaluate(self, eval_points):

        matrix = np.zeros((self.n_basis, len(eval_points), self.dim_codomain))

        basis_evaluations = [b._evaluate(eval_points[:, i:i + 1])
                             for i, b in enumerate(self.basis_list)]

        for i, ev in enumerate(itertools.product(*basis_evaluations)):

            matrix[i, :, 0] = np.prod(ev, axis=0)

        return matrix

    def _derivative_basis_and_coefs(self, coefs, order=1):

        pass

    def basis_of_product(self, other):
        pass

    def rbasis_of_product(self, other):
        pass
