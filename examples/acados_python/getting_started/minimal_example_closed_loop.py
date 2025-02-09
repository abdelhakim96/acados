# -*- coding: future_fstrings -*-
#
# Copyright 2019 Gianluca Frison, Dimitris Kouzoupis, Robin Verschueren,
# Andrea Zanelli, Niels van Duijkeren, Jonathan Frey, Tommaso Sartor,
# Branimir Novoselnik, Rien Quirynen, Rezart Qelibari, Dang Doan,
# Jonas Koenemann, Yutao Chen, Tobias Schöls, Jonas Schlagenhauf, Moritz Diehl
#
# This file is part of acados.
#
# The 2-Clause BSD License
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.;
#

import sys
sys.path.insert(0, 'common')

from acados_template import AcadosOcp, AcadosOcpSolver, AcadosSimSolver
from pendulum_model import export_pendulum_ode_model
from utils import plot_pendulum
import numpy as np
import scipy.linalg

# create ocp object to formulate the OCP
ocp = AcadosOcp()

# set model
model = export_pendulum_ode_model()
ocp.model = model

Tf = 1.0
nx = model.x.size()[0]
nu = model.u.size()[0]
ny = nx + nu
ny_e = nx
N_horizon = 20

# set dimensions
ocp.dims.N = N_horizon
# NOTE: all dimensions but N are now detected automatically in the Python
#  interface, all other dimensions will be overwritten by the detection.

# set cost module
ocp.cost.cost_type = 'LINEAR_LS'
ocp.cost.cost_type_e = 'LINEAR_LS'

Q_mat = 2*np.diag([1e3, 1e3, 1e-2, 1e-2])
R_mat = 2*np.diag([1e-2])

ocp.cost.W = scipy.linalg.block_diag(Q_mat, R_mat)

ocp.cost.W_e = Q_mat

ocp.cost.Vx = np.zeros((ny, nx))
ocp.cost.Vx[:nx,:nx] = np.eye(nx)

Vu = np.zeros((ny, nu))
Vu[4,0] = 1.0
ocp.cost.Vu = Vu

ocp.cost.Vx_e = np.eye(nx)

ocp.cost.yref  = np.zeros((ny, ))
ocp.cost.yref_e = np.zeros((ny_e, ))

# set constraints
Fmax = 80
x0 = np.array([0.0, np.pi, 0.0, 0.0])
ocp.constraints.constr_type = 'BGH'
ocp.constraints.lbu = np.array([-Fmax])
ocp.constraints.ubu = np.array([+Fmax])
ocp.constraints.x0 = x0
ocp.constraints.idxbu = np.array([0])

ocp.solver_options.qp_solver = 'PARTIAL_CONDENSING_HPIPM' # FULL_CONDENSING_QPOASES
ocp.solver_options.hessian_approx = 'GAUSS_NEWTON'
ocp.solver_options.integrator_type = 'ERK'
ocp.solver_options.nlp_solver_type = 'SQP' # SQP_RTI

ocp.solver_options.qp_solver_cond_N = N_horizon

# set prediction horizon
ocp.solver_options.tf = Tf

acados_ocp_solver = AcadosOcpSolver(ocp, json_file = 'acados_ocp_' + model.name + '.json')
# create an integrator with the same settings as used in the OCP solver.
acados_integrator = AcadosSimSolver(ocp, json_file = 'acados_ocp_' + model.name + '.json')

Nsim = 100
simX = np.ndarray((Nsim+1, nx))
simU = np.ndarray((Nsim, nu))

xcurrent = x0
simX[0,:] = xcurrent

# closed loop
for i in range(Nsim):

    # solve ocp
    acados_ocp_solver.set(0, "lbx", xcurrent)
    acados_ocp_solver.set(0, "ubx", xcurrent)

    status = acados_ocp_solver.solve()

    if status != 0:
        raise Exception(f'acados acados_ocp_solver returned status {status}')

    simU[i,:] = acados_ocp_solver.get(0, "u")

    # simulate system
    acados_integrator.set("x", xcurrent)
    acados_integrator.set("u", simU[i,:])

    status = acados_integrator.solve()
    if status != 0:
        raise Exception(f'acados integrator returned status {status}.')

    # update state
    xcurrent = acados_integrator.get("x")
    simX[i+1,:] = xcurrent

# plot results
plot_pendulum(np.linspace(0, Tf/N_horizon*Nsim, Nsim+1), Fmax, simU, simX)
