"""
NAME:
    hb_ha_plotting.py

PURPOSE:
    Provides a module where plotting functions can be called from 
    stack_spectral_data.py for Hb/Ha (Keck) plots
"""

from analysis.balmer_fit import find_nearest, get_best_fit, get_best_fit2, get_best_fit3
import numpy as np

def subplots_setup(ax, ax_list, label, subtitle, num, pos_flux=0, flux=0, 
    pos_amp=0, neg_amp=0, pos_sigma=0, neg_sigma=0, continuum=0):
    '''
    Sets up the subplots for Hb/Ha. Adds emission lines for each subplot
    and sets the ylimits for each row. Also adds flux labels to each subplot.
    '''
    ax.text(0.03,0.97,label,transform=ax.transAxes,fontsize=7,ha='left',
        va='top')
    
    if num%2==0:
        ax.set_title(subtitle,fontsize=8,loc='left')
        if subtitle != 'NB816':
            ax.text(0.97,0.97,'flux='+'{:.4e}'.format((pos_flux))+
                    '\nflux_corr='+'{:.4e}'.format((flux))+
                    '\npos_amp='+'{:.4e}'.format((pos_amp))+
                    '\nneg_amp='+'{:.4e}'.format((neg_amp))+
                    '\npos_sigma='+'{:.4e}'.format((pos_sigma))+
                    '\nneg_sigma='+'{:.4e}'.format((neg_sigma))+
                    '\ncontinuum='+'{:.4e}'.format((continuum)),transform=ax.transAxes,fontsize=7,ha='right',va='top')
    elif num%2==1:
        ymaxval = max(ax.get_ylim())
        [a.set_ylim(ymax=ymaxval) for a in ax_list[num-1:num]]
        ax.text(0.97,0.97,'flux='+'{:.4e}'.format((pos_flux))+
            '\npos_amp='+'{:.4e}'.format((pos_amp))+
            '\npos_sigma='+'{:.4e}'.format((pos_sigma))+
            '\ncontinuum='+'{:.4e}'.format((continuum)),
            transform=ax.transAxes,fontsize=7,ha='right',va='top')
        if subtitle != 'NB816':
            ax_list[num-1].plot([4861,4861],[0,ymaxval],'k',alpha=0.7,zorder=1)
        ax_list[num].plot([6563,6563], [0,ymaxval],'k',alpha=0.7,zorder=1)
        ax_list[num].plot([6548,6548],[0,ymaxval], 'k:',alpha=0.4,zorder=1)
        ax_list[num].plot([6583,6583],[0,ymaxval], 'k:',alpha=0.4,zorder=1)
    #endif
    return ax
#enddef


def subplots_plotting(ax, xval, yval, label, subtitle, dlambda, xmin0, xmax0, tol, num):
    '''
    Plots all the spectra for the subplots for Hg/Hb/Ha. Also calculates
    and returns fluxes and equations of best fit.
    '''
    if not (subtitle=='NB816' and num%2==0):
        good_ii = np.array([x for x in range(len(xval)) if xval[x] >= xmin0 and xval[x] <= xmax0])
        xval = xval[good_ii]
        yval = yval[good_ii]
        ax.plot(xval, yval/1E-17, zorder=2)
    
    flux = 0
    flux2 = 0
    flux3 = 0
    pos_flux = 0
    o1 = 0
    o2 = 0
    o3 = 0

    if 'alpha' in label:
        o1 = get_best_fit(xval, yval, label)
        ax.plot(xval, (o1[3]+o1[0]*np.exp(-0.5*((xval-o1[1])/o1[2])**2))/1E-17, 'r--', zorder=3)
        flux = np.sum(dlambda * (o1[0]*np.exp(-0.5*((xval-o1[1])/o1[2])**2)))
        pos_flux = flux

        peak_idx2_left  = find_nearest(xval, 6548.1-tol)
        peak_idx2_right = find_nearest(xval, 6548.1+tol)
        xval2=xval[peak_idx2_left:peak_idx2_right]
        yval2=yval[peak_idx2_left:peak_idx2_right]
        try:
            o2 = get_best_fit2(xval2, yval2, 6548.1, label)
        except RuntimeError:
            print '(For NII fitting) RuntimeError: Optimal parameters not found: Number of calls to function has reached maxfev = 1000.'
            o2 = [0,0,0,0]
        flux2 = np.sum(dlambda * (o2[0]*np.exp(-0.5*((xval2-o2[1])/o2[2])**2)))
        ax.plot(xval2, (o2[3]+o2[0]*np.exp(-0.5*((xval2-o2[1])/o2[2])**2))/1E-17, 'g,', zorder=3)

        peak_idx3_left = find_nearest(xval, 6583.6-tol)
        peak_idx3_right = find_nearest(xval, 6583.6+tol)
        xval3=xval[peak_idx3_left:peak_idx3_right]
        yval3=yval[peak_idx3_left:peak_idx3_right]
        try:
            o3 = get_best_fit2(xval3, yval3, 6583.6, label)
        except RuntimeError:
            print '(For NII fitting) RuntimeError: Optimal parameters not found: Number of calls to function has reached maxfev = 1000.'
            o3 = [0,0,0,0]
        flux3 = np.sum(dlambda * (o3[0]*np.exp(-0.5*((xval3-o3[1])/o3[2])**2)))
        ax.plot(xval3, (o3[3]+o3[0]*np.exp(-0.5*((xval3-o3[1])/o3[2])**2))/1E-17, 'g,', zorder=3)
    elif 'beta' in label and subtitle!='NB816':
        o1 = get_best_fit3(xval, yval, label)
        pos0 = o1[6]+o1[0]*np.exp(-0.5*((xval-o1[1])/o1[2])**2)
        neg0 = o1[3]*np.exp(-0.5*((xval-o1[4])/o1[5])**2)
        func0 = pos0 + neg0
        ax.plot(xval, func0/1E-17, 'r--', zorder=3)
        ax.plot(xval, pos0/1E-17, 'c--', zorder=2)
        ax.plot(xval, (o1[6]+neg0)/1E-17, 'orange', ls='--', zorder=2)

        idx_small = np.where(np.absolute(xval - o1[1]) <= 2.5*o1[2])[0]

        pos_flux = np.sum(dlambda * (pos0[idx_small] - o1[6]))
        flux = np.sum(dlambda * (pos0[idx_small] - o1[6] - neg0[idx_small]))
        flux2 = 0
        flux3 = 0
    #endif

    ax.set_xlim(xmin0, xmax0)
    ax.set_ylim(ymin=0)
    
    return ax, flux, flux2, flux3, pos_flux, o1
#enddef