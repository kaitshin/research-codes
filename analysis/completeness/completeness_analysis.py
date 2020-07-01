"""
completeness_analysis
====

A set of Python 2.7 codes for completeness analysis of NB-selected galaxies
in the M*-SFR plot
"""

import os

from chun_codes import TimerClass

from datetime import date

from os.path import exists

from astropy.table import Table, vstack

import numpy as np

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

from scipy.interpolate import interp1d

# from ..NB_errors import filt_ref, dNB, lambdac, dBB
from . import filt_ref, dNB, lambdac, dBB
from . import filters, cont0

from . import MLog, cmap_sel, cmap_nosel
from . import EW_lab, Flux_lab, M_lab, SFR_lab
from . import EW_bins, Flux_bins, sSFR_bins, SFR_bins
from . import m_NB, cont_lim, minthres

from .stats import stats_log, avg_sig_label, stats_plot
from .monte_carlo import random_mags
from .select import get_sigma, color_cut, NB_select
from .plotting import avg_sig_plot_init, plot_MACT, plot_mock, plot_completeness, ew_flux_hist
from .properties import compute_EW, dict_prop_maker, derived_properties

import astropy.units as u
from astropy.cosmology import FlatLambdaCDM

cosmo = FlatLambdaCDM(H0=70 * u.km / u.s / u.Mpc, Om0=0.3)

"""
Pass through ew_MC() call
Nsim  = 5000. # Number of modelled galaxies
Nmock = 10    # Number of mocked galaxies
"""

if exists('/Users/cly/GoogleDrive'):
    path0 = '/Users/cly/GoogleDrive/Research/NASA_Summer2015/'
if exists('/Users/cly/Google Drive'):
    path0 = '/Users/cly/Google Drive/NASA_Summer2015/'

npz_path0 = '/Users/cly/data/SDF/MACT/LowM_MainSequence_npz/'
if not exists(npz_path0):
    os.mkdir(npz_path0)

# Dictionary names
npz_NBnames = ['N_mag_mock', 'Ndist_mock', 'Ngal', 'Nmock', 'NB_ref', 'NB_sig_ref']

npz_MCnames = ['EW_seed', 'logEW_MC_ref', 'x_MC0_ref', 'BB_MC0_ref',
               'BB_sig_ref', 'sig_limit_ref', 'NB_sel_ref', 'NB_nosel_ref',
               'EW_flag_ref', 'flux_ref', 'logM_ref', 'NIIHa_ref',
               'logOH_ref', 'HaFlux_ref', 'HaLum_ref', 'logSFR_ref']


def plot_NB_select(ff, t_ax, NB, ctype, linewidth=1, plot4=True):
    t_ax.axhline(y=minthres[ff], linestyle='dashed', color=ctype)

    y3 = color_cut(NB, m_NB[ff], cont_lim[ff])
    t_ax.plot(NB, y3, ctype + '--', linewidth=linewidth)

    y3_int = interp1d(y3, NB)
    NB_break = y3_int(minthres[ff])

    if plot4:
        y4 = color_cut(NB, m_NB[ff], cont_lim[ff], sigma=4.0)
        t_ax.plot(NB, y4, ctype + ':', linewidth=linewidth)

    return NB_break


def get_mag_vs_mass_interp(prefix_ff):
    """
    Purpose:
      Define interpolation function between continuum magnitude and stellar mass

    :param prefix_ff: filter prefix (str)
      Either 'Ha-NB7', 'Ha-NB816', 'Ha-NB921', or 'Ha-NB973'

    :return mass_int: interp1d object for logarithm of stellar mass, logM
    :return std_mass_int: interp1d object for dispersion in logM
    """

    npz_mass_file = path0 + 'Completeness/mag_vs_mass_' + prefix_ff + '.npz'
    npz_mass = np.load(npz_mass_file, allow_pickle=True)
    cont_arr = npz_mass['cont_arr']
    dmag = cont_arr[1] - cont_arr[0]
    mgood = np.where(npz_mass['N_logM'] != 0)[0]

    x_temp = cont_arr + dmag / 2.0
    mass_int = interp1d(x_temp[mgood], npz_mass['avg_logM'][mgood],
                        bounds_error=False, fill_value='extrapolate',
                        kind='linear')

    mbad = np.where(npz_mass['N_logM'] <= 1)[0]
    std0 = npz_mass['std_logM']
    if len(mbad) > 0:
        std0[mbad] = 0.30

    std_mass_int = interp1d(x_temp, std0, fill_value=0.3, bounds_error=False,
                            kind='nearest')
    return mass_int, std_mass_int


def ew_MC(Nsim=5000., Nmock=10, debug=False, redo=False):
    """
    Main function for Monte Carlo realization.  Adopts log-normal
    EW distribution to determine survey sensitivity and impact on
    M*-SFR relation

    Parameters
    ----------
    Nsim: Number of modelled galaxies (int)
    Nmock: Number of mock galaxies for each modelled galaxy (int)
    debug : boolean
      If enabled, a quicker version is executed for test-driven development.
      Default: False
    redo : boolean
      Re-run mock galaxy generation even if file exists. Default: False
    """

    today0 = date.today()
    str_date = "%02i%02i" % (today0.month, today0.day)
    if debug:
        str_date += ".debug"
    mylog = MLog(path0 + 'Completeness/', str_date)._get_logger()

    t0 = TimerClass()
    t0._start()

    prefixes = ['Ha-NB7', 'Ha-NB7', 'Ha-NB816', 'Ha-NB921', 'Ha-NB973']

    # NB statistical filter correction
    filt_corr = [1.289439104, 1.41022358406, 1.29344789854,
                 1.32817034288, 1.29673596942]

    z_NB = lambdac / 6562.8 - 1.0

    npz_slope = np.load(path0 + 'Completeness/NB_numbers.npz',
                        allow_pickle=True)

    logEW_mean_start = np.array([1.25, 1.25, 1.25, 1.25, 0.90])
    logEW_sig_start = np.array([0.15, 0.55, 0.25, 0.35, 0.55])
    n_mean = 4
    n_sigma = 4

    mylog.info('Nsim : ', Nsim)

    NBbin = 0.25

    nrow_stats = 4

    # One file written for all avg and sigma comparisons
    if not debug:
        out_pdf3 = path0 + 'Completeness/ew_MC.avg_sigma.pdf'
        pp3 = PdfPages(out_pdf3)

    ff_range = [0] if debug else range(len(filt_ref))
    mm_range = [0] if debug else range(n_mean)
    ss_range = [0] if debug else range(n_sigma)

    for ff in ff_range:  # loop over filter
        t_ff = TimerClass()
        t_ff._start()
        mylog.info("Working on : " + filters[ff])

        logEW_mean = logEW_mean_start[ff] + 0.1 * np.arange(n_mean)
        logEW_sig = logEW_sig_start[ff] + 0.1 * np.arange(n_sigma)

        comp_shape = (len(mm_range), len(ss_range))
        comp_sSFR = np.zeros(comp_shape)
        # comp_EW   = np.zeros(comp_shape)
        comp_SFR = np.zeros(comp_shape)
        comp_flux = np.zeros(comp_shape)
        comp_EWmean = np.zeros(comp_shape)
        comp_EWsig = np.zeros(comp_shape)

        out_pdf = path0 + 'Completeness/ew_MC_' + filters[ff] + '.pdf'
        if debug:
            out_pdf = out_pdf.replace('.pdf', '.debug.pdf')
        pp = PdfPages(out_pdf)

        # This is cropped to fit
        out_pdf0 = path0 + 'Completeness/ew_MC_' + filters[ff] + '.crop.pdf'
        if debug:
            out_pdf0 = out_pdf0.replace('.pdf', '.debug.pdf')
        pp0 = PdfPages(out_pdf0)

        out_pdf2 = path0 + 'Completeness/ew_MC_' + filters[ff] + '.stats.pdf'
        if debug:
            out_pdf2 = out_pdf2.replace('.pdf', '.debug.pdf')
        pp2 = PdfPages(out_pdf2)

        out_pdf4 = path0 + 'Completeness/ew_MC_' + filters[ff] + '.comp.pdf'
        if debug:
            out_pdf4 = out_pdf4.replace('.pdf', '.debug.pdf')
        pp4 = PdfPages(out_pdf4)

        filt_dict = {'dNB': dNB[ff], 'dBB': dBB[ff], 'lambdac': lambdac[ff]}

        x = np.arange(0.01, 10.00, 0.01)
        EW_ref = compute_EW(x, ff)

        good = np.where(np.isfinite(EW_ref))[0]
        mylog.info('EW_ref (min/max): %f %f ' % (min(EW_ref[good]),
                                                 max(EW_ref[good])))
        EW_int = interp1d(EW_ref[good], x[good], bounds_error=False,
                          fill_value=(-3.0, np.max(EW_ref[good])))

        NBmin = 20.0
        NBmax = m_NB[ff] - 0.25
        NB = np.arange(NBmin, NBmax + NBbin, NBbin)
        mylog.info('NB (min/max): %f %f ' % (min(NB), max(NB)))

        npz_NBfile = npz_path0 + filters[ff] + '_init.npz'

        if not exists(npz_NBfile) or redo:
            N_mag_mock = npz_slope['N_norm0'][ff] * Nsim * NBbin
            N_interp = interp1d(npz_slope['mag_arr'][ff], N_mag_mock)
            Ndist_mock = np.int_(np.round(N_interp(NB)))
            NB_ref = np.repeat(NB, Ndist_mock)

            Ngal = NB_ref.size  # Number of galaxies

            NB_sig = get_sigma(NB, m_NB[ff], sigma=3.0)
            NB_sig_ref = np.repeat(NB_sig, Ndist_mock)

            npz_NBdict = {}
            for name in npz_NBnames:
                npz_NBdict[name] = eval(name)

            if exists(npz_NBfile):
                mylog.info("Overwriting : " + npz_NBfile)
            else:
                mylog.info("Writing : " + npz_NBfile)
            np.savez(npz_NBfile, **npz_NBdict)
        else:
            if not redo:
                mylog.info("File found : " + npz_NBfile)
                npz_NB = np.load(npz_NBfile)

                for key0 in npz_NB.keys():
                    cmd1 = key0 + " = npz_NB['" + key0 + "']"
                    exec (cmd1)

        mock_sz = (Nmock, Ngal)

        # Randomize NB magnitudes. First get relative sigma, then scale by size
        NB_seed = ff
        mylog.info("seed for %s : %i" % (filters[ff], NB_seed))
        NB_MC = random_mags(NB_seed, mock_sz, NB_ref, NB_sig_ref)
        stats_log(NB_MC, "NB_MC", mylog)

        # Read in mag vs mass extrapolation
        mass_int, std_mass_int = get_mag_vs_mass_interp(prefixes[ff])

        lum_dist = cosmo.luminosity_distance(z_NB[ff]).to(u.cm).value

        # Read in EW and fluxes for H-alpha NB emitter sample
        npz_NB_file = path0 + 'Completeness/ew_flux_Ha-' + filters[ff] + '.npz'
        npz_NB = np.load(npz_NB_file)
        NB_EW = npz_NB['NB_EW']
        Ha_Flux = npz_NB['Ha_Flux']

        NBmag = npz_NB['NBmag']
        contmag = npz_NB['contmag']
        logMstar = npz_NB['logMstar']
        Ha_SFR = npz_NB['Ha_SFR']  # metallicity-dependent observed SFR
        Ha_Lum = npz_NB['Ha_Lum']  # filter and [NII] corrected

        spec_flag = npz_NB['spec_flag']
        w_spec = np.where(spec_flag)[0]
        wo_spec = np.where(spec_flag == 0)[0]

        # Statistics for comparisons
        avg_NB = np.average(NB_EW)
        sig_NB = np.std(NB_EW)

        avg_NB_flux = np.average(Ha_Flux)
        sig_NB_flux = np.std(Ha_Flux)

        # Plot sigma and average
        fig3, ax3 = avg_sig_plot_init(filters[ff], logEW_mean, avg_NB, sig_NB,
                                      avg_NB_flux, sig_NB_flux)
        ax3ul = ax3[0][0]
        ax3ll = ax3[1][0]
        ax3ur = ax3[0][1]
        ax3lr = ax3[1][1]

        chi2_EW0 = np.zeros((n_mean, n_sigma))
        chi2_Fl0 = np.zeros((n_mean, n_sigma))

        count = 0
        for mm in mm_range:  # loop over median of EW dist
            comp_EWmean[mm] = logEW_mean[mm]
            for ss in ss_range:  # loop over sigma of EW dist
                comp_EWsig[mm, ss] = logEW_sig[ss]

                npz_MCfile = npz_path0 + filters[ff] + ('_%.2f_%.2f.npz') % (logEW_mean[mm],
                                                                             logEW_sig[ss])

                fig, ax = plt.subplots(ncols=2, nrows=3)
                [[ax00, ax01], [ax10, ax11], [ax20, ax21]] = ax

                plt.subplots_adjust(left=0.105, right=0.98, bottom=0.05,
                                    top=0.98, wspace=0.25, hspace=0.05)

                # This is for statistics plot
                if count % nrow_stats == 0:
                    fig2, ax2 = plt.subplots(ncols=2, nrows=nrow_stats)
                s_row = count % nrow_stats  # For statistics plot

                if not exists(npz_MCfile) or redo:
                    EW_seed = mm * len(ss_range) + ss
                    mylog.info("seed for mm=%i ss=%i : %i" % (mm, ss, EW_seed))
                    np.random.seed(EW_seed)
                    rand0 = np.random.normal(0.0, 1.0, size=Ngal)
                    # This is not H-alpha
                    logEW_MC_ref = logEW_mean[mm] + logEW_sig[ss] * rand0
                    stats_log(logEW_MC_ref, "logEW_MC_ref", mylog)

                    x_MC0_ref = EW_int(logEW_MC_ref)  # NB color excess
                    negs = np.where(x_MC0_ref < 0)
                    if len(negs[0]) > 0:
                        x_MC0_ref[negs] = 0.0
                    stats_log(x_MC0_ref, "x_MC0_ref", mylog)

                    # Selection based on 'true' magnitudes
                    NB_sel_ref, NB_nosel_ref, sig_limit_ref = NB_select(ff, NB_ref, x_MC0_ref)

                    EW_flag_ref = np.zeros(Ngal)
                    EW_flag_ref[NB_sel_ref] = 1

                    BB_MC0_ref = NB_ref + x_MC0_ref
                    BB_sig_ref = get_sigma(BB_MC0_ref, cont_lim[ff], sigma=3.0)

                    dict_prop = dict_prop_maker(NB_ref, BB_MC0_ref, x_MC0_ref,
                                                filt_dict, filt_corr[ff], mass_int,
                                                lum_dist)
                    _, flux_ref, logM_ref, NIIHa_ref, logOH_ref, HaFlux_ref, \
                        HaLum_ref, logSFR_ref = derived_properties(**dict_prop)

                    if exists(npz_MCfile):
                        mylog.info("Overwriting : " + npz_MCfile)
                    else:
                        mylog.info("Writing : " + npz_MCfile)

                    npz_MCdict = {}
                    for name in npz_MCnames:
                        npz_MCdict[name] = eval(name)
                    np.savez(npz_MCfile, **npz_MCdict)
                else:
                    if not redo:
                        mylog.info("File found : " + npz_MCfile)
                        npz_MC = np.load(npz_MCfile)

                        for key0 in npz_MC.keys():
                            cmd1 = key0 + " = npz_MC['" + key0 + "']"
                            exec (cmd1)

                        dict_prop = dict_prop_maker(NB_ref, BB_MC0_ref, x_MC0_ref,
                                                    filt_dict, filt_corr[ff], mass_int,
                                                    lum_dist)

                BB_seed = ff + 5
                mylog.info("seed for broadband, mm=%i ss=%i : %i" % (mm, ss, BB_seed))
                BB_MC = random_mags(BB_seed, mock_sz, BB_MC0_ref, BB_sig_ref)
                stats_log(BB_MC, "BB_MC", mylog)

                x_MC = BB_MC - NB_MC
                stats_log(x_MC, "x_MC", mylog)

                NB_sel, NB_nosel, sig_limit = NB_select(ff, NB_MC, x_MC)

                EW_flag0 = np.zeros(mock_sz)
                EW_flag0[NB_sel[0], NB_sel[1]] = 1

                # Not sure if we should use true logEW or the mocked values
                # logEW_MC = mock_ones(logEW_MC_ref, Nmock)

                dict_prop['NB'] = NB_MC
                dict_prop['BB'] = BB_MC
                dict_prop['x'] = x_MC
                logEW_MC, flux_MC, logM_MC, NIIHa, logOH, HaFlux_MC, HaLum_MC, \
                    logSFR_MC = derived_properties(std_mass_int=std_mass_int,
                                                   **dict_prop)
                stats_log(logEW_MC, "logEW_MC", mylog)
                stats_log(flux_MC, "flux_MC", mylog)
                stats_log(HaFlux_MC, "HaFlux_MC", mylog)

                # Panel (0,0) - NB excess selection plot

                plot_mock(ax00, NB_MC, x_MC, NB_sel, NB_nosel, '', cont0[ff] + ' - ' + filters[ff])

                ax00.axvline(m_NB[ff], linestyle='dashed', color='b')

                temp_x = contmag - NBmag
                plot_MACT(ax00, NBmag, temp_x, w_spec, wo_spec)

                NB_break = plot_NB_select(ff, ax00, NB, 'b')

                N_annot_txt = avg_sig_label('', logEW_mean[mm], logEW_sig[ss],
                                            panel_type='EW')
                N_annot_txt += '\n' + r'$N$ = %i' % NB_MC.size
                ax00.annotate(N_annot_txt, [0.05, 0.95], va='top',
                              ha='left', xycoords='axes fraction')

                # Plot cropped version
                fig0, ax0 = plt.subplots()
                plt.subplots_adjust(left=0.1, right=0.98, bottom=0.10,
                                    top=0.98, wspace=0.25, hspace=0.05)

                plot_mock(ax0, NB_MC, x_MC, NB_sel, NB_nosel, filters[ff], cont0[ff] + ' - ' + filters[ff])
                ax0.axvline(m_NB[ff], linestyle='dashed', color='b')

                temp_x = contmag - NBmag
                plot_MACT(ax0, NBmag, temp_x, w_spec, wo_spec)

                plot_NB_select(ff, ax0, NB, 'b', plot4=False)

                N_annot_txt = avg_sig_label('', logEW_mean[mm], logEW_sig[ss],
                                            panel_type='EW')
                N_annot_txt += '\n' + r'$N$ = %i' % NB_MC.size
                ax0.annotate(N_annot_txt, [0.025, 0.975], va='top',
                             ha='left', xycoords='axes fraction')
                fig0.savefig(pp0, format='pdf')

                # Panel (1,0) - NB mag vs H-alpha flux
                plot_mock(ax10, NB_MC, HaFlux_MC, NB_sel, NB_nosel, filters[ff],
                          Flux_lab)

                plot_MACT(ax10, NBmag, Ha_Flux, w_spec, wo_spec)

                # Panel (0,1) - stellar mass vs H-alpha luminosity

                plot_mock(ax01, logM_MC, HaLum_MC, NB_sel, NB_nosel, '',
                          r'$\log(L_{{\rm H}\alpha})$')

                plot_MACT(ax01, logMstar, Ha_Lum, w_spec, wo_spec)

                # Panel (1,1) - stellar mass vs H-alpha SFR

                plot_mock(ax11, logM_MC, logSFR_MC, NB_sel, NB_nosel, M_lab, SFR_lab)

                plot_MACT(ax11, logMstar, Ha_SFR, w_spec, wo_spec)

                # Plot cropped version
                fig0, ax0 = plt.subplots()
                plt.subplots_adjust(left=0.1, right=0.98, bottom=0.10,
                                    top=0.98, wspace=0.25, hspace=0.05)

                plot_mock(ax0, logM_MC, logSFR_MC, NB_sel, NB_nosel, M_lab, SFR_lab)

                plot_MACT(ax0, logMstar, Ha_SFR, w_spec, wo_spec)
                # ax0.set_ylim([-5,-1])
                fig0.savefig(pp0, format='pdf')

                # Panel (2,0) - histogram of EW
                min_EW = compute_EW(minthres[ff], ff)
                mylog.info("minimum EW : %f " % min_EW)
                ax20.axvline(x=min_EW, color='red')

                No, Ng, binso, \
                    wht0 = ew_flux_hist('EW', mm, ss, ax20, NB_EW, avg_NB,
                                        sig_NB, EW_bins, logEW_mean, logEW_sig,
                                        EW_flag0, logEW_MC, ax3=ax3ul)
                ax20.set_position([0.085, 0.05, 0.44, 0.265])

                good = np.where(EW_flag0)[0]

                # Model comparison plots
                if len(good) > 0:
                    chi2 = stats_plot('EW', ax2, ax3ur, ax20, s_row, Ng, No,
                                      binso, logEW_mean[mm], logEW_sig[ss], ss)
                    chi2_EW0[mm, ss] = chi2

                # Panel (2,1) - histogram of H-alpha fluxes
                No, Ng, binso, \
                    wht0 = ew_flux_hist('Flux', mm, ss, ax21, Ha_Flux,
                                        avg_NB_flux, sig_NB_flux, Flux_bins,
                                        logEW_mean, logEW_sig,
                                        EW_flag0, HaFlux_MC, ax3=ax3ll)
                ax21.set_position([0.53, 0.05, 0.44, 0.265])

                ax21.legend(loc='upper right', fancybox=True, fontsize=6,
                            framealpha=0.75)

                # Model comparison plots
                if len(good) > 0:
                    chi2 = stats_plot('Flux', ax2, ax3lr, ax21, s_row, Ng, No,
                                      binso, logEW_mean[mm], logEW_sig[ss], ss)
                    chi2_Fl0[mm, ss] = chi2

                if s_row != nrow_stats - 1:
                    ax2[s_row][0].set_xticklabels([])
                    ax2[s_row][1].set_xticklabels([])
                else:
                    ax2[s_row][0].set_xlabel(EW_lab)
                    ax2[s_row][1].set_xlabel(Flux_lab)

                # Save each page after each model iteration
                fig.set_size_inches(8, 10)
                fig.savefig(pp, format='pdf')
                plt.close(fig)

                # Save figure for each full page completed
                if s_row == nrow_stats - 1 or count == len(mm_range) * len(ss_range) - 1:
                    fig2.subplots_adjust(left=0.1, right=0.97, bottom=0.08,
                                         top=0.97, wspace=0.13)

                    fig2.set_size_inches(8, 10)
                    fig2.savefig(pp2, format='pdf')
                    plt.close(fig2)
                count += 1

                # Compute and plot completeness
                # Combine over modelled galaxies
                comp_arr = np.sum(EW_flag0, axis=0) / float(Nmock)

                # Plot Type 1 and 2 errors
                cticks = np.arange(0, 1.2, 0.2)

                fig4, ax4 = plt.subplots(nrows=2, ncols=2)
                [[ax400, ax401], [ax410, ax411]] = ax4

                ax4ins0 = inset_axes(ax400, width="40%", height="15%", loc=3,
                                     bbox_to_anchor=(0.025, 0.1, 0.95, 0.25),
                                     bbox_transform=ax400.transAxes)  # LL
                ax4ins1 = inset_axes(ax400, width="40%", height="15%", loc=4,
                                     bbox_to_anchor=(0.025, 0.1, 0.95, 0.25),
                                     bbox_transform=ax400.transAxes)  # LR

                ax4ins0.xaxis.set_ticks_position("top")
                ax4ins1.xaxis.set_ticks_position("top")

                idx0 = [NB_sel_ref, NB_nosel_ref]
                cmap0 = [cmap_sel, cmap_nosel]
                lab0 = ['Type 1', 'Type 2']
                for idx, cmap, ins, lab in zip(idx0, cmap0, [ax4ins0, ax4ins1], lab0):
                    cs = ax400.scatter(NB_ref[idx], x_MC0_ref[idx], edgecolor='none',
                                       vmin=0, vmax=1.0, s=15, c=comp_arr[idx],
                                       cmap=cmap)
                    cb = fig4.colorbar(cs, cax=ins, orientation="horizontal",
                                       ticks=cticks)
                    cb.ax.tick_params(labelsize=8)
                    cb.set_label(lab)

                plot_NB_select(ff, ax400, NB, 'k', linewidth=2)

                ax400.set_xlabel(filters[ff])
                ax400.set_ylim([-0.5, 2.0])
                ax400.set_ylabel(cont0[ff] + ' - ' + filters[ff])

                ax400.annotate(N_annot_txt, [0.025, 0.975], va='top',
                               ha='left', xycoords='axes fraction')

                logsSFR_ref = logSFR_ref - logM_ref
                logsSFR_MC = logSFR_MC - logM_MC

                above_break = np.where(NB_MC <= NB_break)

                t_comp_sSFR, \
                    t_comp_sSFR_ref = plot_completeness(ax401, logsSFR_MC, NB_sel, sSFR_bins,
                                                        ref_arr0=logsSFR_ref,
                                                        above_break=above_break)

                '''t_comp_EW, \
                    t_comp_EW_ref = plot_completeness(ax410, logEW_MC, NB_sel,
                                                      EW_bins, ref_arr0=logEW_MC_ref)
                '''
                t_comp_Fl, \
                    t_comp_Fl_ref = plot_completeness(ax410, HaFlux_MC, NB_sel,
                                                      Flux_bins, ref_arr0=HaFlux_ref)

                t_comp_SFR, \
                    t_comp_SFR_ref = plot_completeness(ax411, logSFR_MC, NB_sel,
                                                       SFR_bins, ref_arr0=logSFR_ref)
                comp_sSFR[mm, ss] = t_comp_sSFR
                comp_SFR[mm, ss] = t_comp_SFR
                comp_flux[mm, ss] = t_comp_Fl

                fig0, ax0 = plt.subplots()
                plt.subplots_adjust(left=0.1, right=0.97, bottom=0.10,
                                    top=0.98, wspace=0.25, hspace=0.05)
                t_comp_SFR = plot_completeness(ax0, logSFR_MC, NB_sel, SFR_bins,
                                               ref_arr0=logSFR_ref, annotate=False)
                ax0.set_ylabel('Completeness')
                ax0.set_xlabel(SFR_lab)
                ax0.set_ylim([0.0, 1.05])
                fig0.savefig(pp0, format='pdf')

                xlabels = [r'$\log({\rm sSFR})$', Flux_lab, SFR_lab]
                for t_ax, xlabel in zip([ax401, ax410, ax411], xlabels):
                    t_ax.set_ylabel('Completeness')
                    t_ax.set_xlabel(xlabel)
                    t_ax.set_ylim([0.0, 1.05])

                # ax410.axvline(x=compute_EW(minthres[ff], ff), color='red')

                plt.subplots_adjust(left=0.09, right=0.98, bottom=0.065,
                                    top=0.98, wspace=0.20, hspace=0.15)
                fig4.set_size_inches(8, 8)
                fig4.savefig(pp4, format='pdf')

                # Plot sSFR vs stellar mass
                fig5, ax5 = plt.subplots()
                plot_mock(ax5, logM_MC, logSFR_MC - logM_MC, NB_sel, NB_nosel, M_lab,
                          r'$\log({\rm sSFR})$')
                plt.subplots_adjust(left=0.09, right=0.98, bottom=0.1, top=0.98)
                fig5.set_size_inches(8, 8)
                fig5.savefig(pp4, format='pdf')

        pp.close()
        pp0.close()
        pp2.close()
        pp4.close()

        ax3ul.legend(loc='upper right', title=r'$\sigma[\log({\rm EW})]$',
                     fancybox=True, fontsize=8, framealpha=0.75, scatterpoints=1)

        # Compute best fit using weighted chi^2
        chi2_wht = np.sqrt(chi2_EW0 ** 2 / 2 + chi2_Fl0 ** 2 / 2)
        b_chi2 = np.where(chi2_wht == np.min(chi2_wht))
        mylog.info("Best chi2 : " + str(b_chi2))
        mylog.info("Best chi2 : (%s, %s) " % (logEW_mean[b_chi2[0]][0],
                                              logEW_sig[b_chi2[1]][0]))
        ax3ur.scatter(logEW_mean[b_chi2[0]] + 0.005 * (b_chi2[1] - 3 / 2.),
                      chi2_EW0[b_chi2], edgecolor='k', facecolor='none',
                      s=100, linewidth=2)
        ax3lr.scatter(logEW_mean[b_chi2[0]] + 0.005 * (b_chi2[1] - 3 / 2.),
                      chi2_Fl0[b_chi2], edgecolor='k', facecolor='none',
                      s=100, linewidth=2)

        fig3.set_size_inches(8, 8)
        fig3.subplots_adjust(left=0.105, right=0.97, bottom=0.065, top=0.98,
                             wspace=0.25, hspace=0.01)

        out_pdf3_each = path0 + 'Completeness/ew_MC_' + filters[ff] + '.avg_sigma.pdf'
        if debug:
            out_pdf3_each = out_pdf3_each.replace('.pdf', '.debug.pdf')
        fig3.savefig(out_pdf3_each, format='pdf')

        if not debug:
            fig3.savefig(pp3, format='pdf')
        plt.close(fig3)

        table_outfile = path0 + 'Completeness/' + filters[ff] + '_completeness_50.tbl'
        if debug:
            table_outfile = table_outfile.replace('.tbl', '.debug.tbl')
        c_size = comp_shape[0] * comp_shape[1]
        comp_arr0 = [comp_EWmean.reshape(c_size), comp_EWsig.reshape(c_size),
                     comp_sSFR.reshape(c_size), comp_SFR.reshape(c_size),
                     comp_flux.reshape(c_size)]
        c_names = ('log_EWmean', 'log_EWsig', 'comp_50_sSFR', 'comp_50_SFR',
                   'comp_50_flux')

        mylog.info("Writing : " + table_outfile)
        comp_tab = Table(comp_arr0, names=c_names)
        comp_tab.write(table_outfile, format='ascii.fixed_width_two_line',
                       overwrite=True)

        # Generate table containing best fit results
        if not debug:
            best_tab0 = comp_tab[b_chi2[0] * len(ss_range) + b_chi2[1]]
            if ff == 0:
                comp_tab0 = best_tab0
            else:
                comp_tab0 = vstack([comp_tab0, best_tab0])

        t_ff._stop()
        mylog.info("ew_MC completed for " + filters[ff] + " in : " + t_ff.format)

    if not debug:
        table_outfile0 = path0 + 'Completeness/best_fit_completeness_50.tbl'
        comp_tab0.write(table_outfile0, format='ascii.fixed_width_two_line',
                        overwrite=True)

    if not debug:
        pp3.close()

    t0._stop()
    mylog.info("ew_MC completed in : " + t0.format)


'''
THIS IS CODE THAT WAS NOT USED FOR CROPPING PDF.  DECIDED TO GENERATE NEW PLOTSX
def crop_pdf(infile, outfile, pp_page):
    with open(infile, "rb") as in_f:
        input1 = PdfFileReader(in_f)
        output = PdfFileWriter()

        numPages = input1.getNumPages()
        print("document has %s pages." % numPages)

        page = input1.getPage(pp_page)
        print(page.mediaBox.getUpperRight_x(), page.mediaBox.getUpperRight_y())
        page.trimBox.lowerLeft = (20, 25)
        page.trimBox.upperRight = (225, 225)
        page.cropBox.lowerLeft = (50, 50)
        page.cropBox.upperRight = (200, 200)
        output.addPage(page)

    with open(outfile, "wb") as out_f:
        output.write(out_f)
#enddef
'''
