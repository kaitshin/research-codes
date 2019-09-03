"""
completeness_analysis
====

A set of Python 2.7 codes for completeness analysis of NB-selected galaxies
in the M*-SFR plot
"""

import sys, os

from chun_codes import systime

from os.path import exists

from astropy.io import fits
from astropy.io import ascii as asc

import numpy as np

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

from scipy.interpolate import interp1d

from NB_errors import ew_flux_dual, fluxline, mag_combine

from NB_errors import filt_ref, dNB, lambdac, dBB, epsilon

from ..mainseq_corrections import niiha_oh_determine

import astropy.units as u
from astropy.cosmology import FlatLambdaCDM
cosmo = FlatLambdaCDM(H0 = 70 * u.km / u.s / u.Mpc, Om0=0.3)

Nsim  = 5000. # Number of modelled galaxies
Nmock = 10    # Number of mocked galaxies

filters = ['NB704','NB711','NB816','NB921','NB973']

NB_filt = np.array([xx for xx in range(len(filt_ref)) if 'NB' in filt_ref[xx]])
for arr in ['filt_ref','dNB','lambdac','dBB','epsilon']:
    cmd1 = arr + ' = np.array('+arr+')'
    exec(cmd1)
    cmd2 = arr + ' = '+arr+'[NB_filt]'
    exec(cmd2)

#Limiting magnitudes for NB and BB data
m_NB  = np.array([26.7134-0.047, 26.0684, 26.9016+0.057, 26.7088-0.109, 25.6917-0.051])
m_BB1 = np.array([28.0829, 28.0829, 27.7568, 26.8250, 26.8250])
m_BB2 = np.array([27.7568, 27.7568, 26.8250, 00.0000, 00.0000])
cont_lim = mag_combine(m_BB1, m_BB2, epsilon)

#Minimum NB excess color for selection
minthres = [0.15, 0.15, 0.15, 0.2, 0.25]

from astropy import log

path0 = '/Users/cly/Google Drive/NASA_Summer2015/'

npz_path0 = '/Users/cly/data/SDF/MACT/LowM_MainSequence_npz/'
if not exists(npz_path0):
    os.mkdir(npz_path0)

m_AB = 48.6

# Common text for labels
EW_lab   = r'$\log({\rm EW}/\AA)$'
Flux_lab = r'$\log(F_{{\rm H}\alpha})$'

EW_bins   = np.arange(0.2,3.0,0.2)
Flux_bins = np.arange(-17.75,-14.00,0.25)

# Colors for each separate points on avg_sigma plots
avg_sig_ctype = ['m','r','g','b','k']

cmap_sel   = plt.cm.Blues
cmap_nosel = plt.cm.Reds

# Dictionary names
npz_NBnames = ['N_mag_mock','Ndist_mock','Ngal','Nmock','NB_ref','NB_sig_ref']

npz_MCnames = ['EW_seed', 'logEW_MC_ref', 'x_MC0_ref', 'BB_MC0_ref',
               'BB_sig_ref', 'sig_limit_ref', 'NB_sel_ref', 'NB_nosel_ref',
               'EW_flag_ref', 'flux_ref', 'logM_ref', 'NIIHa_ref',
               'logOH_ref', 'HaFlux_ref', 'HaLum_ref', 'logSFR_ref']

def get_sigma(x, lim1, sigma=3.0):
    '''
    Magnitude errors based on limiting magnitude

    Parameters
    ----------

    x : Array of magnitudes

    lim1 : float
      3-sigma limiting magnitude for corresponding x

    sigma : float
      Sigma threshold.  Default: 3.0

    Returns
    -------

    dmag : array of magnitude errors
    '''

    SNR = sigma * 10**(-0.4*(x - lim1))

    dmag = 2.5*np.log10(1 + 1/SNR)
    return dmag
#enddef

def avg_sig_label(str0, avg, sigma, type=''):
    '''
    Generate raw strings that contain proper formatting for average and sigma
    EW and fluxes
    '''

    if type == 'EW':
        str0 += r'$\langle\log({\rm EW}_0)\rangle$ = %.2f' % avg
        str0 += '\n' + r'$\sigma[\log({\rm EW}_0)]$ = %.2f' % sigma

    if type == 'Flux':
        str0 += r'$\langle\log(F_{{\rm H}\alpha})\rangle$ = %.2f' % avg
        str0 += '\n' + r'$\sigma[\log(F_{{\rm H}\alpha})]$ = %.2f' % sigma

    return str0
#enddef

def N_avg_sig_label(x0, avg, sigma):
    '''
    String containing average and sigma for ax.legend() labels
    '''

    return r'N: %i  $\langle x\rangle$: %.2f  $\sigma$: %.2f' % \
        (x0.size, avg, sigma)
#enddef

def color_cut(x, lim1, lim2, mean=0.0, sigma=3.0):
    '''
    NB excess color selection based on limiting magnitudes

    Parameters
    ----------

    x : Array of NB magnitudes

    lim1 : float
      3-sigma NB limiting magnitude

    lim2 : float
      3-sigma BB limiting magnitude

    sigma : float
      Sigma threshold.  Default: 3.0

    Returns
    -------

    val : array of 3-sigma allowed BB - NB excess color
    '''

    f1 = (sigma/3.0) * 10**(-0.4*(m_AB+lim1))
    f2 = (sigma/3.0) * 10**(-0.4*(m_AB+lim2))

    f = 10**(-0.4*(m_AB+x))

    val = mean -2.5*np.log10(1 - np.sqrt(f1**2+f2**2)/f)

    return val
#enddef

def plot_NB_select(ff, t_ax, NB, ctype, linewidth=1):
    t_ax.axhline(y=minthres[ff], linestyle='dashed', color=ctype)

    y3 = color_cut(NB, m_NB[ff], cont_lim[ff])
    t_ax.plot(NB, y3, ctype+'--', linewidth=linewidth)
    y4 = color_cut(NB, m_NB[ff], cont_lim[ff], sigma=4.0)
    t_ax.plot(NB, y4, ctype+':', linewidth=linewidth)
#enddef

def NB_select(ff, NB_mag, x_mag):
    '''
    NB excess color selection

    ff : integer for filter

    NB_mag : array of NB magnitudes

    x_mag : array of NB excess colors, continuum - NB
    '''

    sig_limit = color_cut(NB_mag, m_NB[ff], cont_lim[ff])

    NB_sel   = np.where((x_mag >= minthres[ff]) & (x_mag >= sig_limit))
    NB_nosel = np.where((x_mag <  minthres[ff]) | (x_mag <  sig_limit))

    return NB_sel, NB_nosel, sig_limit
#enddef

def correct_NII(log_flux, NIIHa):
    '''
    This returns Halpha fluxes from F_NB using NII/Ha flux ratios for
    correction
    '''
    return log_flux - np.log10(1+NIIHa)
#enddef

def get_NIIHa_logOH(logM):
    '''
    Get [NII]6548,6583/H-alpha flux ratios and oxygen abundance based on
    stellar mass.  Metallicity is from PP04
    '''

    NIIHa = np.zeros(logM.shape)

    low_mass = np.where(logM <= 8.0)
    if len(low_mass[0]) > 0:
        NIIHa[low_mass] = 0.0624396766589

    high_mass = np.where(logM > 8.0)
    if len(high_mass[0]) > 0:
        NIIHa[high_mass] = 0.169429547993*logM[high_mass] - 1.29299670728


    # Compute metallicity
    NII6583_Ha = NIIHa * 1/(1+1/2.96)

    NII6583_Ha_resize = np.reshape(NII6583_Ha, NII6583_Ha.size)
    logOH = niiha_oh_determine(np.log10(NII6583_Ha_resize), 'PP04_N2') - 12.0
    logOH = np.reshape(logOH, logM.shape)

    return NIIHa, logOH
#enddef

def HaSFR_metal_dep(logOH, orig_lums):
    '''
    Determine H-alpha SFR using metallicity and luminosity to follow
    Ly+ 2016 metallicity-dependent SFR conversion
    '''

    y = logOH + 3.31
    log_SFR_LHa = -41.34 + 0.39 * y + 0.127 * y**2

    log_SFR = log_SFR_LHa + orig_lums

    return log_SFR
#enddef

def mag_vs_mass(silent=False, verbose=True):

    '''
    Compares optical photometry against stellar masses to get relationship

    Parameters
    ----------

    silent : boolean
      Turns off stdout messages. Default: False

    verbose : boolean
      Turns on additional stdout messages. Default: True

    Returns
    -------

    Notes
    -----
    Created by Chun Ly, 1 May 2019
    '''

    if silent == False: log.info('### Begin mag_vs_mass : '+systime())

    # NB Ha emitter sample for ID
    NB_file = path0 + 'Main_Sequence/mainseq_corrections_tbl (1).txt'
    log.info("Reading : "+NB_file)
    NB_tab     = asc.read(NB_file)
    NB_HA_Name = NB_tab['NAME0'].data
    NB_Ha_ID   = NB_tab['ID'].data - 1 # Relative to 0 --> indexing

    # Read in stellar mass results table
    FAST_file = path0 + \
                'FAST/outputs/NB_IA_emitters_allphot.emagcorr.ACpsf_fast.GALEX.fout'
    log.info("Reading : "+FAST_file)
    FAST_tab = asc.read(FAST_file)

    logM = FAST_tab['col7'].data

    logM_NB_Ha = logM[NB_Ha_ID]

    NB_catfile = path0 + 'Catalogs/NB_IA_emitters.allcols.colorrev.fix.errors.fits'
    log.info("Reading : "+NB_catfile)
    NB_catdata = fits.getdata(NB_catfile)
    NB_catdata = NB_catdata[NB_Ha_ID]

    cont_mag = np.zeros(len(NB_catdata))

    fig, ax = plt.subplots(ncols=2, nrows=2)

    for filt in filters:
        log.info('### Working on : '+filt)
        NB_idx = [ii for ii in range(len(NB_tab)) if 'Ha-'+filt in \
                  NB_HA_Name[ii]]
        print(" Size : ", len(NB_idx))
        #print(NB_catdata[filt+'_CONT_MAG'])[NB_idx]
        cont_mag[NB_idx] = NB_catdata[filt+'_CONT_MAG'][NB_idx]

    for rr in range(2):
        for cc in range(2):
            if cc == 0: ax[rr][cc].set_ylabel(r'$\log(M/M_{\odot})$')
            if cc == 1: ax[rr][cc].set_yticklabels([])
            ax[rr][cc].set_xlim(19.5,28.5)
            ax[rr][cc].set_ylim(4.0,11.0)

    prefixes = ['Ha-NB7','Ha-NB816','Ha-NB921','Ha-NB973']
    xlabels  = [r"$R_Ci$'", r"$i$'$z$'", "$z$'", "$z$'"]
    annot    = ['NB704,NB711', 'NB816', 'NB921', 'NB973']

    dmag = 0.4

    for ff in range(len(prefixes)):
        col = ff % 2
        row = ff / 2
        NB_idx = np.array([ii for ii in range(len(NB_tab)) if prefixes[ff] in \
                           NB_HA_Name[ii]])
        t_ax = ax[row][col]
        t_ax.scatter(cont_mag[NB_idx], logM_NB_Ha[NB_idx], edgecolor='blue',
                     color='none', alpha=0.5)
        t_ax.set_xlabel(xlabels[ff])
        t_ax.annotate(annot[ff], [0.975,0.975], xycoords='axes fraction',
                      ha='right', va='top')

        x_min    = np.min(cont_mag[NB_idx])
        x_max    = np.max(cont_mag[NB_idx])
        cont_arr = np.arange(x_min, x_max+dmag, dmag)
        avg_logM = np.zeros(len(cont_arr))
        std_logM = np.zeros(len(cont_arr))
        N_logM   = np.zeros(len(cont_arr))
        for cc in range(len(cont_arr)):
            cc_idx = np.where((cont_mag[NB_idx] >= cont_arr[cc]) &
                              (cont_mag[NB_idx] < cont_arr[cc]+dmag))[0]
            if len(cc_idx) > 0:
                avg_logM[cc] = np.average(logM_NB_Ha[NB_idx[cc_idx]])
                std_logM[cc] = np.std(logM_NB_Ha[NB_idx[cc_idx]])
                N_logM[cc]   = len(cc_idx)

        t_ax.scatter(cont_arr+dmag/2, avg_logM, marker='o', color='black',
                     edgecolor='none')
        t_ax.errorbar(cont_arr+dmag/2, avg_logM, yerr=std_logM, capsize=0,
                      linestyle='none', color='black')

        out_npz = path0 + 'Completeness/mag_vs_mass_'+prefixes[ff]+'.npz'
        log.info("Writing : "+out_npz)
        np.savez(out_npz, x_min=x_min, x_max=x_max, cont_arr=cont_arr,
                 avg_logM=avg_logM, std_logM=std_logM, N_logM=N_logM)
    #endfor
    plt.subplots_adjust(left=0.07, right=0.97, bottom=0.08, top=0.97,
                        wspace=0.01)

    out_pdf = path0 + 'Completeness/mag_vs_mass.pdf'
    fig.savefig(out_pdf, bbox_inches='tight')
    if silent == False: log.info('### End mag_vs_mass : '+systime())
#enddef

def get_mag_vs_mass_interp(prefix_ff):
    '''
    Define interpolation function between continuum magnitude and stellr mass

    Parameters
    ----------

    prefix_ff : str
      Either 'Ha-NB7', 'Ha-NB816', 'Ha-NB921', or 'Ha-NB973'

    '''

    npz_mass_file = path0 + 'Completeness/mag_vs_mass_'+prefix_ff+'.npz'
    npz_mass = np.load(npz_mass_file)
    cont_arr = npz_mass['cont_arr']
    dmag     = cont_arr[1]-cont_arr[0]
    mgood    = np.where(npz_mass['N_logM'] != 0)[0]
    mass_int = interp1d(cont_arr[mgood]+dmag/2.0, npz_mass['avg_logM'][mgood],
                        bounds_error=False, fill_value='extrapolate',
                        kind='linear')
    return mass_int
#enddef

def derived_properties(NB, BB, x, filt_dict, filt_corr, mass_int, lum_dist):

    EW, NB_flux = ew_flux_dual(NB, BB, x, filt_dict)

    # Apply NB filter correction from beginning
    NB_flux = np.log10(NB_flux * filt_corr)

    logM = mass_int(BB)
    NIIHa, logOH = get_NIIHa_logOH(logM)

    Ha_Flux = correct_NII(NB_flux, NIIHa)
    Ha_Lum  = Ha_Flux + np.log10(4*np.pi) + 2*np.log10(lum_dist)

    logSFR  = HaSFR_metal_dep(logOH, Ha_Lum)

    return np.log10(EW), NB_flux, logM, NIIHa, logOH, Ha_Flux, Ha_Lum, logSFR
#enddef

def mock_ones(arr0, Nmock):
    '''
    Generate (Nmock,Ngal) array using np.ones() to repeat
    '''

    return np.ones((Nmock,1)) * arr0
#enddef

def random_mags(t_seed, rand_shape, mag_ref, sig_ref):
    '''
    Generate randomized array of magnitudes based on ref values and sigma
    '''

    N_rep = rand_shape[0]

    np.random.seed = t_seed
    return mock_ones(mag_ref, N_rep) + np.random.normal(size=rand_shape) * \
        mock_ones(sig_ref, N_rep)

#enddef

def get_EW_Flux_distribution():
    '''
    Retrieve NB excess emission-line EW and fluxes from existing tables
    '''

    # NB Ha emitter sample for ID
    NB_file = path0 + 'Main_Sequence/mainseq_corrections_tbl (1).txt'
    log.info("Reading : "+NB_file)
    NB_tab      = asc.read(NB_file)
    NB_HA_Name  = NB_tab['NAME0'].data
    NB_Ha_ID    = NB_tab['ID'].data - 1 # Relative to 0 --> indexing
    NII_Ha_corr = NB_tab['nii_ha_corr_factor'].data # This is log(1+NII/Ha)
    filt_corr   = NB_tab['filt_corr_factor'].data # This is log(f_filt)
    zspec0      = NB_tab['zspec0'].data

    NB_catfile = path0 + 'Catalogs/NB_IA_emitters.allcols.colorrev.fix.errors.fits'
    log.info("Reading : "+NB_catfile)
    NB_catdata = fits.getdata(NB_catfile)
    NB_catdata = NB_catdata[NB_Ha_ID]

    # These are the raw measurements
    NB_EW   = np.zeros(len(NB_catdata))
    NB_Flux = np.zeros(len(NB_catdata))

    Ha_EW   = np.zeros(len(NB_catdata))
    Ha_Flux = np.zeros(len(NB_catdata))

    logMstar = np.zeros(len(NB_catdata))
    Ha_SFR   = np.zeros(len(NB_catdata))
    Ha_Lum   = np.zeros(len(NB_catdata))

    NBmag   = np.zeros(len(NB_catdata))
    contmag = np.zeros(len(NB_catdata))

    spec_flag = np.zeros(len(NB_catdata))

    for filt in filters:
        log.info('### Working on : '+filt)
        NB_idx = np.array([ii for ii in range(len(NB_tab)) if 'Ha-'+filt in \
                           NB_HA_Name[ii]])
        print(" Size : ", len(NB_idx))
        NB_EW[NB_idx]   = np.log10(NB_catdata[filt+'_EW'][NB_idx])
        NB_Flux[NB_idx] = NB_catdata[filt+'_FLUX'][NB_idx]

        Ha_EW[NB_idx]   = (NB_EW   + NII_Ha_corr + filt_corr)[NB_idx]
        Ha_Flux[NB_idx] = (NB_Flux + NII_Ha_corr + filt_corr)[NB_idx]

        NBmag[NB_idx]   = NB_catdata[filt+'_MAG'][NB_idx]
        contmag[NB_idx] = NB_catdata[filt+'_CONT_MAG'][NB_idx]

        logMstar[NB_idx] = NB_tab['stlr_mass'][NB_idx]
        Ha_SFR[NB_idx]   = NB_tab['met_dep_sfr'][NB_idx]
        Ha_Lum[NB_idx]   = NB_tab['obs_lumin'][NB_idx] + \
                           (NII_Ha_corr + filt_corr)[NB_idx]

        with_spec = np.where((zspec0[NB_idx] > 0) & (zspec0[NB_idx] < 9))[0]
        with_spec = NB_idx[with_spec]
        spec_flag[with_spec] = 1

        out_npz = path0 + 'Completeness/ew_flux_Ha-'+filt+'.npz'
        log.info("Writing : "+out_npz)
        np.savez(out_npz, NB_ID=NB_catdata['ID'][NB_idx], NB_EW=NB_EW[NB_idx],
                 NB_Flux=NB_Flux[NB_idx], Ha_EW=Ha_EW[NB_idx],
                 Ha_Flux=Ha_Flux[NB_idx], NBmag=NBmag[NB_idx],
                 contmag=contmag[NB_idx], spec_flag=spec_flag[NB_idx],
                 logMstar=logMstar[NB_idx], Ha_SFR=Ha_SFR[NB_idx],
                 Ha_Lum=Ha_Lum[NB_idx])
    #endfor

#enddef

def NB_numbers():
    '''
    Uses SExtractor catalog to look at number of NB galaxies vs magnitude
    '''

    NB_path = '/Users/cly/data/SDF/NBcat/'
    NB_phot_files = [NB_path+filt+'/sdf_pub2_'+filt+'.cat.mask' for \
                     filt in filters]

    out_pdf = path0 + 'Completeness/NB_numbers.pdf'

    fig, ax_arr = plt.subplots(nrows=3, ncols=2)

    bin_size = 0.25
    bins = np.arange(17.0,28,bin_size)

    NB_slope0 = np.zeros(len(filters))

    N_norm0 = []
    mag_arr = []

    for ff in range(len(filters)):
        print('Reading : '+NB_phot_files[ff])
        phot_tab = asc.read(NB_phot_files[ff])
        MAG_APER = phot_tab['col13'].data

        row = int(ff / 2)
        col = ff % 2

        ax = ax_arr[row][col]

        N, m_bins, _ = ax.hist(MAG_APER, bins=bins, align='mid', color='black',
                               linestyle='solid', histtype='step',
                               label='N = '+str(len(MAG_APER)))

        det0  = np.where((m_bins >= 18.0) & (m_bins <= m_NB[ff]))[0]
        p_fit = np.polyfit(m_bins[det0], np.log10(N[det0]), 1)

        det1    = np.where((m_bins >= 20.0) & (m_bins <= m_NB[ff]))[0]
        mag_arr += [m_bins[det1]]
        N_norm0 += [N[det1] / bin_size / np.sum(N[det1])]

        NB_slope0[ff] = p_fit[0]

        fit   = np.poly1d(p_fit)
        fit_lab = 'P[0] = %.3f  P[1] = %.3f' % (p_fit[1], p_fit[0])
        ax.plot(m_bins, 10**(fit(m_bins)), 'r--', label=fit_lab)

        ax.axvline(m_NB[ff], linestyle='dashed', linewidth=1.5)
        ax.legend(loc='lower right', fancybox=True, fontsize=8, framealpha=0.75)
        ax.annotate(filters[ff], [0.025,0.975], xycoords='axes fraction',
                    ha='left', va='top', fontsize=10)
        ax.set_yscale('log')
        ax.set_ylim([1,5e4])
        ax.set_xlim([16.5,28.0])

        if col == 0:
            ax.set_ylabel(r'$N$')

        if col == 1:
            ax.yaxis.set_ticklabels([])

        if row == 0 or (row == 1 and col == 0):
            ax.xaxis.set_ticklabels([])
        else:
            ax.set_xlabel('NB [mag]')
    #endfor

    ax_arr[2][1].axis('off')

    plt.subplots_adjust(left=0.105, right=0.98, bottom=0.05, top=0.98,
                        wspace=0.025, hspace=0.025)
    fig.savefig(out_pdf, bbox_inches='tight')

    out_npz = out_pdf.replace('.pdf', '.npz')
    np.savez(out_npz, filters=filters, bin_size=bin_size, NB_slope0=NB_slope0,
             mag_arr=mag_arr, N_norm0=N_norm0)
#enddef

def avg_sig_plot_init(t_filt, logEW_mean, avg_NB, sig_NB, avg_NB_flux,
                      sig_NB_flux):
    '''
    Initialize fig and axes objects for avg_sigma plot and set matplotlib
    aesthetics
    '''

    xlim  = [min(logEW_mean)-0.05,max(logEW_mean)+0.05]
    ylim1 = [avg_NB-sig_NB-0.05, avg_NB+sig_NB+0.15]
    ylim2 = [avg_NB_flux-sig_NB_flux-0.05, avg_NB_flux+sig_NB_flux+0.15]

    xticks = np.arange(xlim[0],xlim[1],0.1)
    fig3, ax3 = plt.subplots(ncols=2, nrows=2)

    ax3[0][0].axhline(y=avg_NB, color='black', linestyle='dashed')
    ax3[0][0].axhspan(avg_NB-sig_NB, avg_NB+sig_NB, alpha=0.5, color='black')
    ax3[0][0].set_xlim(xlim)
    ax3[0][0].set_xticks(xticks)
    #ax3[0][0].set_ylim(ylim1)
    ax3[0][0].set_ylabel(EW_lab)
    ax3[0][0].set_xticklabels([])
    ax3_txt = avg_sig_label(t_filt+'\n', avg_NB, sig_NB, type='EW')
    ax3[0][0].annotate(ax3_txt, (0.025,0.975), xycoords='axes fraction',
                    ha='left', va='top', fontsize=11)

    ax3[1][0].axhline(y=avg_NB_flux, color='black', linestyle='dashed')
    ax3[1][0].axhspan(avg_NB_flux-sig_NB_flux, avg_NB_flux+sig_NB_flux,
                      alpha=0.5, color='black')
    ax3[1][0].set_xlim(xlim)
    ax3[1][0].set_xticks(xticks)
    #ax3[1][0].set_ylim(ylim2)
    ax3[1][0].set_xlabel(EW_lab)
    ax3[1][0].set_ylabel(Flux_lab)
    ax3_txt = avg_sig_label('', avg_NB_flux, sig_NB_flux, type='Flux')
    ax3[1][0].annotate(ax3_txt, (0.025,0.975), xycoords='axes fraction',
                       ha='left', va='top', fontsize=11)

    ax3[0][1].set_xlim(xlim)
    ax3[0][1].set_xticks(xticks)
    ax3[0][1].set_ylabel(r'$\chi^2_{\nu}$')
    ax3[0][1].set_xticklabels([])
    ax3[0][1].set_ylim([0.11,100])
    ax3[0][1].set_yscale('log')

    ax3[1][1].set_xlim(xlim)
    ax3[1][1].set_xticks(xticks)
    ax3[1][1].set_ylabel(r'$\chi^2_{\nu}$')
    ax3[1][1].set_xlabel(EW_lab)
    ax3[1][1].set_ylim([0.11,100])
    ax3[1][1].set_yscale('log')

    return fig3, ax3
#endef

def plot_MACT(ax, x0, y0, w_spec, wo_spec):
    '''
    Plot MACT spectroscopic and photometric sample in various sub-panel

    ax : matplotlib.axes._subplots.AxesSubplot
       sub-Axis to plot

    x0 : list or numpy.array
       Array to plot on x-axis

    y0 : list or numpy.array
       Array to plot on y-axis

    w_spec: numpy.array
       Index array indicating which sources with spectra

    wo_spec: numpy.array
       Index array indicating which sources without spectra (i.e., photometric)
    '''

    ax.scatter(x0[w_spec], y0[w_spec], color='k', edgecolor='none',
               alpha=0.5, s=5)
    ax.scatter(x0[wo_spec], y0[wo_spec], facecolor='none', edgecolor='k',
               alpha=0.5, s=5)
#enddef

def plot_mock(ax, x0, y0, NB_sel, NB_nosel, xlabel, ylabel):
    '''
    Plot mocked galaxies in various sub-panel

    ax : matplotlib.axes._subplots.AxesSubplot
       sub-Axis to plot

    x0 : list or numpy.array
       Array to plot on x-axis

    y0 : list or numpy.array
       Array to plot on y-axis

    NB_sel: numpy.array
       Index array indicating which sources are NB selected

    wo_spec: numpy.array
       Index array indicating which sources are not NB selected

    xlabel: str
       String for x-axis.  Set to '' to not show a label

    xlabel: str
       String for y-axis.  Set to '' to not show a label
    '''

    is1, is2 = NB_sel[0], NB_sel[1]
    in1, in2 = NB_nosel[0], NB_nosel[1]

    ax.hexbin(x0[is1,is2], y0[is1,is2], gridsize=100, mincnt=1, cmap=cmap_sel,
              linewidth=0.2)
    ax.hexbin(x0[in1,in2], y0[in1,in2], gridsize=100, mincnt=1, cmap=cmap_nosel,
              linewidth=0.2)
    #ax.scatter(x0[is1,is2], y0[is1,is2], alpha=0.25, s=2, edgecolor='none')
    #ax.scatter(x0[in1,in2], y0[in1,in2], alpha=0.25, s=2, edgecolor='red',
    #           linewidth=0.25, facecolor='none')
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    if xlabel == '':
        ax.set_xticklabels([])
#enddef

#def get_completeness(EW_flag0, Nmock):
#    comp_arr = np.sum(EW_flag0, axis=0)/float(Nmock) # Combine over
#
#   
##enddef

def ew_flux_hist(type0, mm, ss, t2_ax, x0, avg_x0, sig_x0, x0_bins, logEW_mean,
                 logEW_sig, EW_flag0, x0_arr0, ax3=None):
    '''
    Generate histogram plots for EW or flux
    '''

    if type0 == 'EW':
        x0_lab = EW_lab
    if type0 == 'Flux':
        x0_lab = Flux_lab

    label_x0 = N_avg_sig_label(x0, avg_x0, sig_x0)
    No, binso, _ = t2_ax.hist(x0, bins=x0_bins, align='mid', color='black',
                              alpha=0.5, linestyle='solid', edgecolor='none',
                              histtype='stepfilled', label=label_x0)
    t2_ax.axvline(x=avg_x0, color='black', linestyle='solid', linewidth=1.5)

    good = np.where(EW_flag0)

    # Normalize relative to selected sample
    if len(good[0]) > 0:
        finite = np.where(np.isfinite(x0_arr0))

        norm0 = float(len(x0))/len(good[0])
        wht0  = np.repeat(norm0, x0_arr0.size)
        wht0  = np.reshape(wht0, x0_arr0.shape)

        avg_MC = np.average(x0_arr0[finite])
        sig_MC = np.std(x0_arr0[finite])
        label0 = N_avg_sig_label(x0_arr0, avg_MC, sig_MC)

        N, bins, _ = t2_ax.hist(x0_arr0[finite], bins=x0_bins, weights=wht0[finite],
                                align='mid', color='black', linestyle='dashed',
                                edgecolor='black', histtype='step', label=label0)
        t2_ax.axvline(x=avg_MC, color='black', linestyle='dashed', linewidth=1.5)

        avg_gd = np.average(x0_arr0[good[0],good[1]])
        sig_gd = np.std(x0_arr0[good[0],good[1]])
        label1 = N_avg_sig_label(good[0], avg_gd, sig_gd)
        Ng, binsg, _ = t2_ax.hist(x0_arr0[good], bins=x0_bins, weights=wht0[good],
                                  align='mid', alpha=0.5, color='blue',
                                  edgecolor='blue', linestyle='solid',
                                  histtype='stepfilled', label=label1)
        t2_ax.axvline(x=avg_gd, color='blue', linestyle='solid', linewidth=1.5)

        t2_ax.legend(loc='upper right', fancybox=True, fontsize=6, framealpha=0.75)
        t2_ax.set_xlabel(x0_lab)
        t2_ax.set_yscale('log')
        t2_ax.set_ylim([0.1,1e3])
        if type0 == 'EW':
            t2_ax.set_ylabel(r'$N$')
            t2_ax.set_xlim([0.0,2.95])
        if type0 == 'Flux':
            t2_ax.set_ylabel('')
            t2_ax.set_yticklabels(['']*5)
            t2_ax.set_xlim([-18.0,-14.0])
            t2_ax.set_xticks(np.arange(-17.5,-13.5,1.0))
            t2_ax.set_xticks(np.arange(-17.5,-13.5,1.0))

        as_label = ''
        if mm == 0: as_label = '%.2f' % logEW_sig[ss]

        if type(ax3) != type(None):
            temp_x = [logEW_mean[mm]+0.005*(ss-3/2.)]
            ax3.scatter(temp_x, [avg_gd], marker='o', s=40, edgecolor='none',
                        color=avg_sig_ctype[ss], label=as_label)
            ax3.errorbar(temp_x, [avg_gd], yerr=[sig_gd], capsize=0,
                         elinewidth=1.5, ecolor=avg_sig_ctype[ss], fmt=None)

    return No, Ng, binso, wht0
#enddef

def stats_plot(type0, ax2, ax3, ax, s_row, Ng, No, binso, EW_mean, EW_sig, ss):
    '''
    Plot statistics (chi^2, model vs data comparison) for each model

    type0: str
       Either 'EW' or 'Flux'

    ax2 : matplotlib.axes._subplots.AxesSubplot
       matplotlib axes for stats plot

    ax3 : matplotlib.axes._subplots.AxesSubplot
       matplotlib axes for avg_sigma plot

    ax : matplotlib.axes._subplots.AxesSubplot
       matplotlib axes for main plot

    s_row: int
       Integer for row for ax2

    EW_mean: float
       Value of median logEW in model

    EW_sig: float
       Value of sigma logEW in model

    ss: int
       Integer indicating index for sigma
    '''

    delta    = (Ng-No)/np.sqrt(Ng + No)

    if type0 == 'EW':   pn = 0
    if type0 == 'Flux': pn = 1

    ax2[s_row][pn].axhline(0.0, linestyle='dashed') # horizontal line at zero

    ax2[s_row][pn].scatter(binso[:-1], delta)
    no_use = np.where((Ng == 0) | (No == 0))[0]

    if len(no_use) > 0:
        ax2[s_row][pn].scatter(binso[:-1][no_use], delta[no_use], marker='x',
                               color='r', s=20)

    #ax2[s_row][pn].set_ylabel(r'1 - $N_{\rm mock}/N_{\rm data}$')
    if type0 == 'EW':
        ax2[s_row][pn].set_ylabel(r'$(N_{\rm mock} - N_{\rm data})/\sigma$')

        annot_txt  = r'$\langle\log({\rm EW}_0)\rangle = %.2f$  ' % EW_mean
        annot_txt += r'$\sigma[\log({\rm EW}_0)] = %.2f$' % EW_sig
        ax2[s_row][pn].set_title(annot_txt, fontdict={'fontsize': 10}, loc='left')

    # Compute chi^2
    use_bins = np.where((Ng != 0) & (No != 0))[0]
    if len(use_bins) > 2:
        fit_chi2 = np.sum(delta[use_bins]**2)/(len(use_bins)-2)
        c_txt = r'$\chi^2_{\nu}$ = %.2f' % fit_chi2

        ax3.scatter([EW_mean+0.005*(ss-3/2.)], [fit_chi2],
                    marker='o', s=40, color=avg_sig_ctype[ss],
                    edgecolor='none')
    else:
        print("Too few bins")
        c_txt = r'$\chi^2_{\nu}$ = Unavailable'

    ax.annotate(c_txt, [0.025,0.975], xycoords='axes fraction',
                ha='left', va='top')
    c_txt += '\n' + r'N = %i' % len(use_bins)
    ax2[s_row][pn].annotate(c_txt, [0.975,0.975], ha='right',
                            xycoords='axes fraction', va='top')
#enddef

def ew_MC(debug=False, redo=False):
    '''
    Main function for Monte Carlo realization.  Adopts log-normal
    EW distribution to determine survey sensitivity and impact on
    M*-SFR relation

    Parameters
    ----------

    debug : boolean
      If enabled, a quicker version is executed for test-driven developement.
      Default: False

    redo : boolean
      Re-run mock galaxy generation even if file exists. Default: False

    '''

    prefixes = ['Ha-NB7','Ha-NB7','Ha-NB816','Ha-NB921','Ha-NB973']

    # NB statistical filter correction
    filt_corr = [1.289439104,   1.41022358406, 1.29344789854,
                 1.32817034288, 1.29673596942]

    z_NB     = lambdac/6562.8 - 1.0

    npz_slope = np.load(path0 + 'Completeness/NB_numbers.npz')

    logEW_mean_start = np.array([1.25, 1.45, 1.25, 1.25, 1.75])
    logEW_sig_start  = np.array([0.15, 0.55, 0.25, 0.35, 0.55])
    n_mean  = 4
    n_sigma = 4

    print('Nsim : ', Nsim)

    NBbin = 0.25

    nrow_stats = 4

    # One file written for all avg and sigma comparisons
    if not debug:
        out_pdf3 = path0 + 'Completeness/ew_MC.avg_sigma.pdf'
        pp3 = PdfPages(out_pdf3)

    ff_range = [0] if debug else range(len(filt_ref))
    mm_range = [0] if debug else range(n_mean)
    ss_range = [0] if debug else range(n_sigma)

    for ff in ff_range: # loop over filter
        print("Working on : "+filters[ff])

        logEW_mean = logEW_mean_start[ff] + 0.1*np.arange(n_mean)
        logEW_sig  = logEW_sig_start[ff]  + 0.1*np.arange(n_sigma)

        out_pdf = path0 + 'Completeness/ew_MC_'+filters[ff]+'.pdf'
        if debug: out_pdf = out_pdf.replace('.pdf','.debug.pdf')
        pp = PdfPages(out_pdf)

        out_pdf2 = path0 + 'Completeness/ew_MC_'+filters[ff]+'.stats.pdf'
        if debug: out_pdf2 = out_pdf2.replace('.pdf','.debug.pdf')
        pp2 = PdfPages(out_pdf2)

        out_pdf4 = path0 + 'Completeness/ew_MC_'+filters[ff]+'.comp.pdf'
        if debug: out_pdf4 = out_pdf4.replace('.pdf','.debug.pdf')
        pp4 = PdfPages(out_pdf4)

        filt_dict = {'dNB': dNB[ff], 'dBB': dBB[ff], 'lambdac': lambdac[ff]}

        x      = np.arange(0.01,10.00,0.01)
        y_temp = 10**(-0.4 * x)
        EW_ref = np.log10(dNB[ff]*(1 - y_temp)/(y_temp - dNB[ff]/dBB[ff]))

        good = np.where(np.isfinite(EW_ref))[0]
        EW_int = interp1d(EW_ref[good], x[good], bounds_error=False,
                          fill_value=(-3.0, np.max(EW_ref[good])))

        NBmin = 20.0
        NBmax = m_NB[ff]-0.25
        NB = np.arange(NBmin,NBmax+NBbin,NBbin)
        print('NB (min/max)', min(NB), max(NB))

        npz_NBfile = npz_path0 + filters[ff]+'_init.npz'

        if not exists(npz_NBfile) or redo == True:
            N_mag_mock = npz_slope['N_norm0'][ff] * Nsim * NBbin
            N_interp   = interp1d(npz_slope['mag_arr'][ff], N_mag_mock)
            Ndist_mock = np.int_(np.round(N_interp(NB)))
            NB_ref     = np.repeat(NB, Ndist_mock)

            Ngal = NB_ref.size # Number of galaxies

            NB_sig     = get_sigma(NB, m_NB[ff], sigma=3.0)
            NB_sig_ref = np.repeat(NB_sig, Ndist_mock)

            npz_NBdict = {}
            for name in npz_NBnames:
                npz_NBdict[name] = eval(name)

            if exists(npz_NBfile):
                print("Overwriting : "+npz_NBfile)
            else:
                print("Writing : "+npz_NBfile)
            np.savez(npz_NBfile, **npz_NBdict)
        else:
            if redo == False:
                print("File found : " + npz_NBfile)
                npz_NB = np.load(npz_NBfile)

                for key0 in npz_NB.keys():
                    cmd1 = key0+" = npz_NB['"+key0+"']"
                    exec(cmd1)

        mock_sz = (Nmock,Ngal)

        # Randomize NB magnitudes. First get relative sigma, then scale by size
        NB_seed = ff
        NB_MC = random_mags(NB_seed, mock_sz, NB_ref, NB_sig_ref)

        # Read in mag vs mass extrapolation
        mass_int = get_mag_vs_mass_interp(prefixes[ff])

        lum_dist = cosmo.luminosity_distance(z_NB[ff]).to(u.cm).value

        # Read in EW and fluxes for H-alpha NB emitter sample
        npz_NB_file = path0 + 'Completeness/ew_flux_Ha-'+filters[ff]+'.npz'
        npz_NB      = np.load(npz_NB_file)
        NB_EW    = npz_NB['NB_EW']
        Ha_Flux  = npz_NB['Ha_Flux']

        NBmag    = npz_NB['NBmag']
        contmag  = npz_NB['contmag']
        logMstar = npz_NB['logMstar']
        Ha_SFR   = npz_NB['Ha_SFR'] # metallicity-dependent observed SFR
        Ha_Lum   = npz_NB['Ha_Lum'] # filter and [NII] corrected

        spec_flag = npz_NB['spec_flag']
        w_spec    = np.where(spec_flag)[0]
        wo_spec   = np.where(spec_flag == 0)[0]

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

        count = 0
        for mm in mm_range: # loop over median of EW dist
            for ss in ss_range: # loop over sigma of EW dist

                npz_MCfile = npz_path0 + filters[ff] + ('_%.2f_%.2f.npz') \
                             % (logEW_mean[mm], logEW_sig[ss])

                fig, ax = plt.subplots(ncols=2, nrows=3)
                [[ax00,ax01],[ax10,ax11],[ax20,ax21]] = ax
                plt.subplots_adjust(left=0.105, right=0.98, bottom=0.05,
                                    top=0.98, wspace=0.25, hspace=0.05)

                # This is for statistics plot
                if count % nrow_stats == 0:
                    fig2, ax2 = plt.subplots(ncols=2, nrows=nrow_stats)
                s_row = count % nrow_stats # For statistics plot

                if not exists(npz_MCfile) or redo == True:
                    EW_seed = mm*len(ss_range) + ss
                    np.random.seed = EW_seed
                    rand0 = np.random.normal(0.0, 1.0, size=Ngal)
                    # This is not H-alpha
                    logEW_MC_ref = logEW_mean[mm] + logEW_sig[ss]*rand0

                    x_MC0_ref = EW_int(logEW_MC_ref) # NB color excess
                    negs = np.where(x_MC0_ref < 0)
                    if len(negs) > 0:
                        x_MC0_ref[negs] = 0.0

                    # Selection based on 'true' magnitudes
                    NB_sel_ref, NB_nosel_ref, sig_limit_ref = NB_select(ff, NB_ref, x_MC0_ref)

                    EW_flag_ref = np.zeros(Ngal)
                    EW_flag_ref[NB_sel_ref] = 1

                    BB_MC0_ref = NB_ref + x_MC0_ref
                    BB_sig_ref = get_sigma(BB_MC0_ref, cont_lim[ff], sigma=3.0)

                    dict_prop = {'NB':NB_ref, 'BB':BB_MC0_ref, 'x':x_MC0_ref,
                                 'filt_dict':filt_dict,
                                 'filt_corr':filt_corr[ff],
                                 'mass_int':mass_int, 'lum_dist':lum_dist}
                    _, flux_ref, logM_ref, NIIHa_ref, logOH_ref, HaFlux_ref, \
                        HaLum_ref, logSFR_ref = derived_properties(**dict_prop)

                    if exists(npz_MCfile):
                        print("Overwriting : "+npz_MCfile)
                    else:
                        print("Writing : "+npz_MCfile)

                    npz_MCdict = {}
                    for name in npz_MCnames:
                        npz_MCdict[name] = eval(name)
                    np.savez(npz_MCfile, **npz_MCdict)
                else:
                    if redo == False:
                        print("File found : " + npz_MCfile)
                        npz_MC = np.load(npz_MCfile)

                        for key0 in npz_MC.keys():
                            cmd1 = key0+" = npz_MC['"+key0+"']"
                            exec(cmd1)

                BB_seed = ff + 5
                BB_MC = random_mags(BB_seed, mock_sz, BB_MC0_ref, BB_sig_ref)

                x_MC  = BB_MC - NB_MC

                NB_sel, NB_nosel, sig_limit = NB_select(ff, NB_MC, x_MC)

                EW_flag0 = np.zeros(mock_sz)
                EW_flag0[NB_sel[0],NB_sel[1]] = 1

                # Not sure if we should use true logEW or the mocked values
                # logEW_MC = mock_ones(logEW_MC_ref, Nmock)

                dict_prop['NB'] = NB_MC
                dict_prop['BB'] = BB_MC
                dict_prop['x']  = x_MC
                logEW_MC, flux_MC, logM_MC, NIIHa, logOH, HaFlux_MC, HaLum_MC, \
                    logSFR_MC = derived_properties(**dict_prop)

                # Panel (0,0) - NB excess selection plot

                plot_mock(ax00, NB_MC, x_MC, NB_sel, NB_nosel, '', 'cont - NB')

                temp_x = contmag-NBmag
                plot_MACT(ax00, NBmag, temp_x, w_spec, wo_spec)

                plot_NB_select(ff, ax00, NB, 'b')

                annot_txt = avg_sig_label('', logEW_mean[mm], logEW_sig[ss],
                                          type='EW')
                annot_txt += '\n' + r'$N$ = %i' % NB_MC.size
                ax00.annotate(annot_txt, [0.05,0.95], va='top',
                              ha='left', xycoords='axes fraction')


                # Panel (1,0) - NB mag vs H-alpha flux
                plot_mock(ax10, NB_MC, HaFlux_MC, NB_sel, NB_nosel, 'NB',
                          Flux_lab)

                plot_MACT(ax10, NBmag, Ha_Flux, w_spec, wo_spec)


                # Panel (0,1) - stellar mass vs H-alpha luminosity

                plot_mock(ax01, logM_MC, HaLum_MC, NB_sel, NB_nosel, '',
                          r'$\log(L_{{\rm H}\alpha})$')

                plot_MACT(ax01, logMstar, Ha_Lum, w_spec, wo_spec)


                # Panel (1,1) - stellar mass vs H-alpha SFR

                plot_mock(ax11, logM_MC, logSFR_MC, NB_sel, NB_nosel,
                          r'$\log(M_{\star}/M_{\odot})$', r'$\log({\rm SFR}({\rm H}\alpha))$')

                plot_MACT(ax11, logMstar, Ha_SFR, w_spec, wo_spec)

                # Panel (2,0) - histogram of EW
                No, Ng, binso, \
                    wht0 = ew_flux_hist('EW', mm, ss, ax20, NB_EW, avg_NB,
                                        sig_NB, EW_bins, logEW_mean, logEW_sig,
                                        EW_flag0, logEW_MC, ax3=ax3ul)
                ax20.set_position([0.085,0.05,0.44,0.265])

                good = np.where(EW_flag0)[0]

                # Model comparison plots
                if len(good) > 0:
                    stats_plot('EW', ax2, ax3ur, ax20, s_row, Ng, No, binso,
                               logEW_mean[mm], logEW_sig[ss], ss)

                # Panel (2,1) - histogram of H-alpha fluxes
                No, Ng, binso, \
                    wht0 = ew_flux_hist('Flux', mm, ss, ax21, Ha_Flux,
                                        avg_NB_flux, sig_NB_flux, Flux_bins,
                                        logEW_mean, logEW_sig,
                                        EW_flag0, HaFlux_MC, ax3=ax3ll)
                ax21.set_position([0.53,0.05,0.44,0.265])

                ax21.legend(loc='upper right', fancybox=True, fontsize=6,
                                framealpha=0.75)

                # Model comparison plots
                if len(good) > 0:
                    stats_plot('Flux', ax2, ax3lr, ax21, s_row, Ng, No, binso,
                               logEW_mean[mm], logEW_sig[ss], ss)

                if s_row != nrow_stats-1:
                    ax2[s_row][0].set_xticklabels([])
                    ax2[s_row][1].set_xticklabels([])
                else:
                    ax2[s_row][0].set_xlabel(EW_lab)
                    ax2[s_row][1].set_xlabel(Flux_lab)

                # Save each page after each model iteration
                fig.set_size_inches(8,10)
                fig.savefig(pp, format='pdf')
                plt.close(fig)

                # Save figure for each full page completed
                if s_row == nrow_stats-1 or count == len(logEW_mean)*len(logEW_sig)-1:
                    fig2.subplots_adjust(left=0.1, right=0.97, bottom=0.08,
                                         top=0.97, wspace=0.13)

                    fig2.set_size_inches(8,10)
                    fig2.savefig(pp2, format='pdf')
                    plt.close(fig2)
                count += 1


            # Compute and plot completeness
            comp_arr = np.sum(EW_flag0, axis=0)/float(Nmock) # Combine over modelled galaxies

            # Plot Type 1 and 2 errors
            cticks = np.arange(0,1.2,0.2)

            fig4, ax4 = plt.subplots(nrows=2, ncols=2)
            [[ax400, ax401], [ax410, ax411]] = ax4

            ax4ins0 = inset_axes(ax400, width="33%", height="3%", loc=6) #LL
            ax4ins1 = inset_axes(ax400, width="33%", height="3%", loc=7) #LR

            ax4ins0.xaxis.set_ticks_position("top")
            ax4ins1.xaxis.set_ticks_position("top")

            idx0  = [NB_sel_ref, NB_nosel_ref]
            cmap0 = [cmap_sel, cmap_nosel]
            lab0  = ['Type 1', 'Type 2']
            for idx,cmap,ins,lab in zip(idx0, cmap0, [ax4ins0, ax4ins1], lab0):
                cs = ax400.scatter(NB_ref[idx], x_MC0_ref[idx], edgecolor='none',
                                   vmin=0, vmax=1.0, s=15, c=comp_arr[idx],
                                   cmap=cmap)
                cb = fig4.colorbar(cs, cax=ins, orientation="horizontal",
                                   ticks=cticks)
                cb.ax.tick_params(labelsize=8)
                cb.set_label(lab)

            plot_NB_select(ff, ax400, NB, 'k', linewidth=2)

            ax400.set_xlabel('NB')
            ax400.set_ylim([-0.25,2.0])
            ax400.set_ylabel('cont - NB')

            annot_txt = avg_sig_label('', logEW_mean[mm], logEW_sig[ss],
                                      type='EW')
            annot_txt += '\n' + r'$N$ = %i' % NB_MC.size
            ax400.annotate(annot_txt, [0.025,0.975], va='top',
                           ha='left', xycoords='axes fraction')

            plt.subplots_adjust(left=0.09, right=0.97, bottom=0.08, top=0.98,
                                wspace=0.05)
            fig4.savefig(pp4, format='pdf')
            #endfor
        #endfor

        pp.close()
        pp2.close()
        pp4.close()

        ax3ul.legend(loc='upper right', title=r'$\sigma[\log({\rm EW}_0)]$',
                     fancybox=True, fontsize=8, framealpha=0.75, scatterpoints=1)

        fig3.set_size_inches(8,8)
        fig3.subplots_adjust(left=0.105, right=0.97, bottom=0.065, top=0.98,
                             wspace=0.25, hspace=0.01)

        out_pdf3_each = path0 + 'Completeness/ew_MC_'+filters[ff]+'.avg_sigma.pdf'
        if debug: out_pdf3_each = out_pdf3_each.replace('.pdf','.debug.pdf')
        fig3.savefig(out_pdf3_each, format='pdf')

        if not debug:
            fig3.savefig(pp3, format='pdf')
        plt.close(fig3)


    #endfor

    if not debug:
        pp3.close()
