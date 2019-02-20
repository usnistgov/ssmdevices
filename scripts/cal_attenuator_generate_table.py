# DGK 2019-02-01

import numpy as np
import pandas as pd
from pathlib import Path

p = Path(r'O:\67205sharing\WirelessCoexistence_VA_Characterizations\Data\11604210014')

files = sorted([n for n in p.iterdir() if str(n).lower().endswith('.csv')])

thrus = {}

for f in files:
    atten = float(f.name[:-len(f.suffix)].split('_')[-1].replace('pt','.'))
#     print(f)
    table = pd.read_table(f, sep=';', comment='#', index_col='freq[Hz]').iloc[:,:-1]
    table = pd.DataFrame(table.iloc[:,::2].values+1j*table.iloc[:,1::2].values,
                         index=table.index,
                         columns=['S11','S21','S12','S22'])
    thrus[atten] = 0.5*(table['S12']+table['S21'])
    
thrus = pd.DataFrame(thrus)
# thrus.values[:] = 10*np.log10(np.abs(thrus.values)**2)
thrus.values[:] /= np.abs(thrus.loc[:,0].values[:,np.newaxis])

thrus.sort_index(axis=1, inplace=True)
thrus.index.name = 'Frequency(Hz)'

vector_mean_bw = 0.02e9
mag_mean_bw = 0.1e9

if thrus.index[1] - thrus.index[0] < vector_mean_bw:
    thrus['averaging_group'] = (thrus.index/vector_mean_bw).astype(int)
    thru_vector_mean=thrus.reset_index().groupby('averaging_group').mean().reset_index().drop('averaging_group',axis=1).set_index('Frequency(Hz)')
else:
    thru_vector_mean = thrus

if thru_vector_mean.index[1] - thru_vector_mean.index[0] < vector_mean_bw:
    thru_vector_mean['averaging_group'] = (thru_vector_mean.index/mag_mean_bw).astype(int)
    thru_mag_mean=np.abs(thru_vector_mean).reset_index().groupby('averaging_group').mean().reset_index().drop('averaging_group',axis=1).set_index('Frequency(Hz)')
else:
    thru_mag_mean = thru_vector_mean

thru_mag_mean.columns = thru_mag_mean.columns.astype(float)
thru_mag_mean.index = thru_mag_mean.index.astype(float)
thru_mag_mean.values[:] /= np.abs(thru_mag_mean.loc[:,0].values[:,np.newaxis])
attens = -20*np.log10(np.abs(thru_mag_mean))

attens.to_csv(str(p)+'.csv.xz', compression='xz', float_format='%.3f')