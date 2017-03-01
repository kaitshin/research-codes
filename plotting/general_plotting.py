"""
NAME:
    general_plotting.py

PURPOSE:
    Provides a module where plotting functions can be called from 
    stack_spectral_data.py for both Hg/Hb/Ha and Hb/Ha (MMT, Keck)
    plots
"""

import numpy as np

def get_name_index_matches(NAME0, inst_str0, inst_dict, *args, **kwargs):
    '''
    Returns the indexes from which the kwargs name is in the ordered NAME0
    array and the kwargs instr is in the ordered inst_dict dict.
    '''
    namematch = kwargs['namematch']
    instr     = kwargs['instr']
    index = np.array([x for x in range(len(NAME0)) if namematch in NAME0[x] and
                      inst_str0[x] in inst_dict[instr]])
    return index
#enddef

def get_index_list(NAME0, inst_str0, inst_dict, instr):
    '''
    Helper function. Returns an index_list for either MMT or Keck 
    based on instr keyword

    Considers by-filter
    '''
    if instr=='MMT':
        index_0 = get_name_index_matches(NAME0, inst_str0, inst_dict, 
            namematch='Ha-NB704',instr=instr)
        index_1 = get_name_index_matches(NAME0, inst_str0, inst_dict, 
            namematch='Ha-NB711',instr=instr)
        index_2 = get_name_index_matches(NAME0, inst_str0, inst_dict, 
            namematch='Ha-NB816',instr=instr)
        index_3 = get_name_index_matches(NAME0, inst_str0, inst_dict, 
            namematch='Ha-NB921',instr=instr)
        index_4 = get_name_index_matches(NAME0, inst_str0, inst_dict, 
            namematch='Ha-NB973',instr=instr)
        return [index_0]*3+[index_1]*3+[index_2]*3+[index_3]*3+[index_4]*3
    elif instr=='Keck':
        index_0 = get_name_index_matches(NAME0, inst_str0, inst_dict, 
            namematch='Ha-NB816',instr=instr)
        index_1 = get_name_index_matches(NAME0, inst_str0, inst_dict, 
            namematch='Ha-NB921',instr=instr)
        index_2 = get_name_index_matches(NAME0, inst_str0, inst_dict, 
            namematch='Ha-NB973',instr=instr)
        return [index_0]*2+[index_1]*2+[index_2]*2
    else:
        print 'error'
        return 0
#enddef

def get_index_list2(stlr_mass, inst_str0, inst_dict, instr):
    '''
    Helper function. Returns an index_list for either MMT or Keck 
    based on instr keyword

    Considers by-stellarmass. For now, goes in 20% percentile bins.
    '''
    good_stlr_mass = np.array([x for x in stlr_mass if x > 0])

    if instr=='MMT':
        perc20 = np.percentile(good_stlr_mass, 20)
        index_0 = np.array([x for x in range(len(stlr_mass)) 
            if (stlr_mass[x]>0 and stlr_mass[x]<=perc20) 
            and inst_str0[x] in inst_dict[instr]])
        perc40 = np.percentile(good_stlr_mass, 40)
        index_1 = np.array([x for x in range(len(stlr_mass)) 
            if (stlr_mass[x]>perc20 and stlr_mass[x]<=perc40) 
            and inst_str0[x] in inst_dict[instr]])
        perc60 = np.percentile(good_stlr_mass, 60)
        index_2 = np.array([x for x in range(len(stlr_mass)) 
            if (stlr_mass[x]>perc40 and stlr_mass[x]<=perc60) 
            and inst_str0[x] in inst_dict[instr]])
        perc80 = np.percentile(good_stlr_mass, 80)
        index_3 = np.array([x for x in range(len(stlr_mass)) 
            if (stlr_mass[x]>perc60 and stlr_mass[x]<=perc80) 
            and inst_str0[x] in inst_dict[instr]])
        perc100 = np.percentile(good_stlr_mass, 100)        
        index_4 = np.array([x for x in range(len(stlr_mass)) 
            if (stlr_mass[x]>perc80 and stlr_mass[x]<=perc100) 
            and inst_str0[x] in inst_dict[instr]])
        return [index_0]*3+[index_1]*3+[index_2]*3+[index_3]*3+[index_4]*3
    # elif instr=='Keck':
    #     return 0
    else:
        print 'error'
        return 0
#enddef

def get_iter_lists(instr, stlr=False):
    '''
    Helper function. Returns  for either MMT or Keck
    based on instr keyword

    Returns different subtitle_list based on stlr param
    '''
    if instr=='MMT':
        xmin_list = np.array([4341,4861,6563]*5)-60
        xmax_list = np.array([4341,4861,6563]*5)+60
        label_list=[r'H$\gamma$',r'H$\beta$',r'H$\alpha$']*5
        if stlr==False:
            subtitle_list = ['NB704']*3+['NB711']*3+['NB816']*3+['NB921']*3+['NB973']*3
        else: #stlr==True:
            subtitle_list = ['perc20']*3+['perc40']*3+['perc60']*3+['perc80']*3+['perc100']*3
        return (xmin_list, xmax_list, label_list, subtitle_list)
    elif instr=='Keck':
        xmin_list = np.array([4861,6563]*3)-60
        xmax_list = np.array([4861,6563]*3)+60
        label_list=[r'H$\beta$',r'H$\alpha$']*3
        if stlr==False:
            subtitle_list = ['NB816']*2+['NB921']*2+['NB973']*2
        # else: #stlr==True:
        #     return 0
        return (xmin_list, xmax_list, label_list, subtitle_list)
    else:
        print 'error'
        return 0
#enddef

def final_plot_setup(f, title):
    '''
    For the passed in figure, adjusts tick parameter sizes,
    adds minorticks and a suptitle, and adjusts spacing

    Works for both Hg/Hb/Ha and Hb/Ha plots
    '''
    [a.tick_params(axis='both', labelsize='6') for a in f.axes[:]]
    [a.minorticks_on() for a in f.axes[:]]

    f.suptitle(title, size=15)    
    f.subplots_adjust(wspace=0.2)
    f.subplots_adjust(hspace=0.2)
    
    return f
#enddef