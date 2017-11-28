import os
import numpy as np
from bluesky.plans import (scan, subs_wrapper, abs_set, pchain, count, list_scan,
                           adaptive_scan, reset_positions_wrapper)
from bluesky.callbacks import LiveTable, LivePlot, LiveFit, LiveFitPlot
from bluesky.plan_tools import print_summary
from lmfit import Model, Parameter
from lmfit.models import VoigtModel, LinearModel
from lmfit.lineshapes import voigt


def MED(init_gas, other_gas, minT, maxT, num_steps, num_steady, num_trans, num_loops=2):
    """
    1. Start flowing the initial gas.
    2. Scan the temperature from minT to maxT in `num_steps` evenly-spaced steps.
    3. Hold temperature at maxT and take  `num_steady` images.
    4. Repeat (2) and (3) `num_loops` times.
    5. Switch the gas to `other_gas` and take `num_trans` acquisitions.
    6. Switch it back and take another `num_trans` acquisitions.

    Example
    -------
    Set the gasses. They can be in any other, nothing to do with
    the order they are used in the plan.
    >>> gas.gas_list = ['O2', 'CO2']

    Optionally, preview the plan.
    >>> print_summary(MED('O2', 'C02', 200, 300, 21, 20, 60))

    Execute it.
    >>> RE(MED('O2', 'C02', 200, 300, 21, 20, 60))

    """
    # Step 1
    yield from abs_set(gas, init_gas)
    # Steps 2 and 3 in a loop.
    for _ in range(num_loops):
        yield from subs_wrapper(scan([pe1, gas.current_gas], eurotherm, minT, maxT, num_steps),
                            LiveTable([eurotherm, gas.current_gas]))
        yield from subs_wrapper(count([pe1], num_steady), LiveTable([]))
    # Step 4
    yield from abs_set(gas, other_gas)
    yield from subs_wrapper(count([pe1], num_steady), LiveTable([]))
    # Step 6
    yield from abs_set(gas, init_gas)
    yield from subs_wrapper(count([pe1], num_steady), LiveTable([]))

def Ecal(guessed_energy, guessed_amplitude=1000, margin=0.5):
    """
    Energy calibration scan


    Parameters
    ----------
    guessed_energy : number
        units of keV
    guessed_amplitude : number, optional
        detector units, defaults to 1000
    margin : number, optional
        how far to scan in two theta beyond the 
        guessed left and right peaks, default 0.5

    Example
    -------

    Execute an energy calibration scan with default steps.
    >>> RE(Ecal(68))
    """
    # Based on the guessed energy, compute where the peaks should be centered
    # in theta. This will be used as an initial guess for peak-fitting.
    D = np.array([4.15772, 2.94676, 2.40116])  # d spacings of LaB6
    guessed_wavelength = 12.398 / guessed_energy  # angtroms
    guessed_centers = np.rad2deg(2 * np.arcsin(guessed_wavelength / (2 * D)))
    _range = max(guessed_centers) + margin
    start, stop = -_range, +_range
    print('guessed_wavelength={} [Angstroms]'.format(guessed_wavelength))
    print('guessed_centers={} [in 2 theta DEGREES]'.format(guessed_centers))
    print('will scan from {} to {}'.format(start, stop))

    def peaks(x, c0, wavelength, a1, a2, a3, sigma):
        c1, c2, c3 = np.rad2deg(2 * np.arcsin(wavelength / (2 * D)))
        result = (voigt(x=x, amplitude=a1, center=c0 - c1, sigma=sigma) +
                  voigt(x=x, amplitude=a1, center=c0 + c1, sigma=sigma) +
                  voigt(x=x, amplitude=a2, center=c0 - c2, sigma=sigma) +
                  voigt(x=x, amplitude=a2, center=c0 + c2, sigma=sigma) +
                  voigt(x=x, amplitude=a3, center=c0 - c3, sigma=sigma) +
                  voigt(x=x, amplitude=a3, center=c0 + c3, sigma=sigma))
        return result
                  
    model = Model(peaks) + LinearModel()

    init_guess = {'intercept': 200, 'slope': 0, 'sigma': 0.1, 'c0': 0,
                  'wavelength': guessed_wavelength}
    for i, center in enumerate(guessed_centers):
        init_guess.update({'a%d' % (1 + i): Parameter('a%d' % (1 + i), guessed_amplitude, min=0)})
    lf = LiveFit(model, 'sc_chan1', {'x': 'tth_cal'}, init_guess,
                 update_every=5)

    table = LiveTable(['tth_cal', 'sc_chan1'])
    fig, ax = plt.subplots()  # explitly create figure, axes to use below
    plot = LivePlot('sc_chan1', 'tth_cal', linestyle='none', marker='o', ax=ax)
    lfp = LiveFitPlot(lf, ax=ax, color='r')
    subs = [table, plot, lfp]

    plan = adaptive_scan([sc], 'sc_chan1', tth_cal, start, stop, min_step=0.005,
                          max_step=0.08, target_delta=100, backstep=True)

    plan = subs_wrapper(plan, subs)
    plan = reset_positions_wrapper(plan, [tth_cal])
    yield from plan
    print(lf.result.values)
    print('WAVELENGTH: {} [Angstroms]'.format(lf.result.values['wavelength']))
