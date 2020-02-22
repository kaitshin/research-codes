from os.path import join
from os.path import dirname
from glob import glob
import ast

from astropy.io import ascii as asc
from astropy.io import fits

import numpy as np
import matplotlib.pyplot as plt

from chun_codes import match_nosort

path0 = '/Users/cly/GoogleDrive/Research/NASA_Summer2015/Plots/color_plots'

co_dir = dirname(__file__)


def draw_color_selection_lines(filt, ax, xra, yra):

    # NB704 and NB711 emitters
    if 'NB7' in filt:
        # Excluding this diagonal line
        # x1 = np.arange(0.30, 1.20, 0.01)
        # ax.plot(x1, 1.70 * x1 + 0.0)

        # These are the color selection for H-alpha
        x2 = np.arange(-0.2, 0.3, 0.01)
        ax.plot(x2, 0.82 * x2 + 0.264, 'k--', linewidth=1.5)
        ax.plot(x2, 2.5 * x2 - 0.24, 'k--', linewidth=1.5)

        # Color selection for other lines
        # Exclude for purpose of color selection in Shin+2020 paper
        # if filt == 'NB704':
        #    ax.plot(x1, 0.8955*x1 + 0.02533, 'b--')
        #    ax.plot([0.2136, 0.3], [0.294]*2, 'b--')
        # if filt == 'NB711':
        #    x3 = np.array([0.35, 1.2])
        #    ax.plot(x3, 0.8955*x3 - 0.0588, 'b--')
        #    ax.plot([0.1960, 0.35], [0.25]*2, 'b--')

    # NB816 emitters
    if filt == 'NB816':
        # Color selection for H-alpha
        ax.plot([0.45, 0.45], [0.8, 2.0], 'k--', linewidth=1.5)

        x1 = np.arange(-0.60, 0.45, 0.01)
        ax.plot(x1, 2*x1 - 0.1, 'k--', linewidth=1.5)

        # Color selection for other lines
        # Exclude this selection of weird emitters
        # x0 = [1.0, 2.0, 2.0, 1.0]
        # y0 = [1.0, 1.0, 2.0, 2.0]
        # ax.plot(x0 + [1.0], y0 + [1.0])

    # NB921 emitters
    if filt == 'NB921':
        # Color selection for H-alpha emitters
        x_val = [xra[0], 0.45]
        x1 = np.arange(x_val[0], x_val[1], 0.01)
        y1 = x1 * 1.46 + 0.58
        ax.plot(x1, y1, 'k--', linewidth=1.5)

        # Vertical dashed line
        ax.plot(np.repeat(x_val[1], 2), [max(y1), yra[1]], 'k--', linewidth=1.5)

    # NB973 emitters:
    if filt == 'NB973':
        # Color selection for H-alpha emitters
        x_val = [0.18, 0.55]
        x1 = np.arange(x_val[0], x_val[1], 0.01)
        y1 = x1 * 2.423 + 0.06386
        ax.plot(x1, y1, 'k--', linewidth=1.5)

        # Vertical dashed line
        ax.plot(np.repeat(x_val[1], 2), [1.4, 3.0], 'k--', linewidth=1.5)

        # Horizontal dashed line
        ax.plot([xra[0], 0.18], [0.5, 0.5], 'k--', linewidth=1.5)


def read_config_file():
    config_file = join(co_dir, 'NB_color_plot.txt')

    config_tab = asc.read(config_file, format='commented_header')

    return config_tab


def read_SE_file(infile):
    print("Reading : " + infile)

    SE_tab = asc.read(infile)

    mag  = SE_tab['col13']  # aperture photometry (col #13)
    dmag = SE_tab['col15']  # aperture photometry error (col #15)

    return mag, dmag


def latex_label_formatting(label):
    new_label = label.replace('R', 'R_C').replace('i', 'i^{\prime}')

    return r'${}$'.format(new_label)


def color_plot_generator(NB_cat_path, filt, config_tab=None, ax=None):
    """
    Purpose:
      Generate two-color plots for include in paper (pre referee request)
      These plots illustrate the identification of NB excess emitters
      based on their primary emission line (H-alpha, [OIII], or [OII])
      in the NB filter

    :param NB_cat_path: str containing the path to NB-based SExtractor catalog
    :param filt: str containing the filter name
    """

    make_single_plot = 0
    if not ax:
        make_single_plot = 1

    # Read in NB excess emitter catalog
    search0 = join(NB_cat_path, filt, '{}emitters.fits'.format(filt))
    NB_emitter_file = glob(search0)[0]
    print("NB emitter catalog : " + NB_emitter_file)

    NB_tab = fits.getdata(NB_emitter_file)

    # Define SExtractor photometric catalog filenames
    search0 = join(NB_cat_path, filt, 'sdf_pub2_*_{}.cat.mask'.format(filt))
    SE_files = glob(search0)

    # Remove z- or zr-band files
    SE_files = [file0 for file0 in SE_files if '_z' not in file0]

    # Read in ID's from SExtractor catalog
    SEx_ID = np.loadtxt(SE_files[0], usecols=0)

    NB_idx, SEx_idx = match_nosort(NB_tab.ID, SEx_ID)
    if NB_idx.size != len(NB_tab):
        print("Issue with table!")
        print("Exiting!")
        return

    if not config_tab:
        config_tab = read_config_file()

    f_idx = np.where(config_tab['filter'] == filt)[0][0]  # config index

    # Read in SExtractor photometric catalogs
    mag_arr = {}
    for file0 in SE_files:
        mag, dmag = read_SE_file(file0)
        temp = file0.replace(join(NB_cat_path, filt, 'sdf_pub2_'), '')
        broad_filt = temp.replace('_{}.cat.mask'.format(filt), '')
        mag_arr[broad_filt+'_mag'] = mag[SEx_idx]
        mag_arr[broad_filt+'_dmag'] = dmag[SEx_idx]

    dict_keys = mag_arr.keys()

    # Define broad-band colors
    if 'V_mag' in dict_keys and 'R_mag' in dict_keys:
        VR = mag_arr['V_mag'] - mag_arr['R_mag']
    if 'R_mag' in dict_keys and 'i_mag' in dict_keys:
        Ri = mag_arr['R_mag'] - mag_arr['i_mag']
    if 'B_mag' in dict_keys and 'V_mag' in dict_keys:
        BV = mag_arr['B_mag'] - mag_arr['V_mag']
    if 'B_mag' in dict_keys and 'R_mag' in dict_keys:
        BR = mag_arr['B_mag'] - mag_arr['R_mag']

    x_title = config_tab['xtitle'][f_idx].replace('-', ' - ')
    y_title = config_tab['ytitle'][f_idx].replace('-', ' - ')
    x_title = latex_label_formatting(x_title)
    y_title = latex_label_formatting(y_title)

    xra = ast.literal_eval(config_tab['xra'][f_idx])
    yra = ast.literal_eval(config_tab['yra'][f_idx])

    if make_single_plot:
        out_pdf = join(path0, filt + '.pdf')

        fig, ax = plt.subplots()

    # Define axis to plot
    exec("x_arr = {}".format(config_tab['x_color'][f_idx]))
    exec("y_arr = {}".format(config_tab['y_color'][f_idx]))
    ax.scatter(x_arr, y_arr, marker='o', color='black', s=2)  # black circles

    ax.set_xlim(xra)
    ax.set_ylim(yra)

    ax.set_xlabel(x_title)
    ax.set_ylabel(y_title)

    ax.minorticks_on()  # Add minor tick marks
    ax.tick_params(which='both', direction='in')  # ticks on the inside

    draw_color_selection_lines(filt, ax, xra, yra)

    if make_single_plot:
        fig.set_size_inches(8, 8)
        fig.savefig(out_pdf, bbox_inches='tight')


def generate_paper_plot():
    """
    Purpose:
      Generates 3x2 panel figure showing color selection for H-alpha emitters

    :return: PDF file generated
    """

    NB_cat_path = '/Users/cly/data/SDF/NBcat/'

    config_tab = read_config_file()

    n_cols = 3
    n_rows = 2
    fig, ax = plt.subplots(ncols=n_cols, nrows=n_rows)

    filters = ['NB704', 'NB711', 'NB816', 'NB921', 'NB973']

    for ii, filt in zip(range(len(filters)), filters):
        row = ii // n_cols
        col = ii % n_cols
        t_ax = ax[row][col]
        color_plot_generator(NB_cat_path, filt, config_tab=config_tab, ax=t_ax)

        if 'NB7' in filt:
            t_ax.set_xlabel('')
            t_ax.set_xticklabels([])  # Remove x-tick labels

        if col == 1:
            t_ax.set_ylabel('')       # Remove label
            t_ax.set_yticklabels([])  # Remove y-tick labels
        # Change x-limit for R-i colors
        if col <= 1:
            t_ax.set_xlim(-0.45, 1.25)

        if col == 2:
            t_ax.yaxis.tick_right()
            t_ax.yaxis.set_label_position("right")

    ax[1][2].axis('off')  # Exclude bottom right panel

    plt.subplots_adjust(hspace=0.025, wspace=0.03)

    fig.set_size_inches(6.5, 4)

    out_pdf = join(path0, 'color_selection.pdf')

    fig.savefig(out_pdf, bbox_inches='tight')
