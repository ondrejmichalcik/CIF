# COMPOSITE INDICATORS
# MINIMAL PIPELINE

import os
os.chdir('C:/path/') # Set path to CIF folder

from CI_functions import *
import pandas as pd
import re
import datetime


# SETTINGS

print(os.environ['X13PATH']) # Check the availability of X-13ARIMA-SEATS model (downloaded from https://www.census.gov/srd/www/x13as/)

bw = False # True for black and white visualisations

country = 'CZE' # Select target country

# OUTPUT DIRECTORY

strDate = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M")

outputDir = os.path.join('plots_' + country + '_' + strDate)
os.makedirs(outputDir, exist_ok = True)


# 1) DATA LOAD (loading data from OECD API)

data_all, subjects_all, measures_all = createDataFrameFromOECD(countries = [country], dsname = 'MEI', frequency = 'M')
data_rs, subjects_rs, measures_rs = createDataFrameFromOECD(countries = [country], dsname = 'QNA', subject = ['B1_GE'], frequency = 'Q')


# 1a) leading indicators: Component series

colMultiInd = data_all.columns.names.index('subject')

ind_LOCO = subjects_all['id'].apply(lambda x: re.search(r'\bLOCO', x) != None)
subjects_LOCO = subjects_all[ind_LOCO]

# 1b) Leading indicators: Reference series

ind_LORS = subjects_all['id'].apply(lambda x: re.search(r'\bLORS', x) != None)
subjects_LORS = subjects_all[ind_LORS]


# 1c) Leading indicators: CLI

ind_LOLI = subjects_all['id'].apply(lambda x: re.search(r'\bLOLI', x) != None)
subjects_LOLI = subjects_all[ind_LOLI]

# 1d) Candidate time series

subjects_adj = subjects_all[-(ind_LOCO | ind_LORS | ind_LOLI)]
data_adj = data_all.select(lambda x: x[colMultiInd] in list(subjects_adj['id']), axis = 1)

                    
# 2) DATA TRANSFORMATIONS

# 2.1) REFERENCE SERIES

# 2.1a) Priority list of reference series (GDP) and frequency conversion

rsPriorityList = [ 'LNBQRSA' # Best fit with OECD reference series
                , 'CQR'
                , 'LNBQR'
                , 'DNBSA'
                , 'DOBSA'
                , 'CQRSA'
                , 'CARSA'
                , 'GPSA'
                , 'GYSA'
                , 'CPCARSA'
                , 'VIXOBSA'
                , 'VOBARSA'
                , 'VPVOBARSA'
                , 'HCPCARSA'
                , 'HVPVOBARSA'
                ]

if (data_rs.shape[0] > 0):
    
    rsq = getOnlyBestMeasure(df = data_rs, priorityList = rsPriorityList)
    rsq = getRidOfMultiindex(df = rsq)
    rsq = renameQuarterlyIndex(df = rsq)
    rsq = getIndexAsDate(df = rsq)
    rs = createMonthlySeries(df = rsq)
    rs.dropna(inplace = True)


# 2.1b) Seasonal adjustment, outlier filtering and short-term prediction
#   & Cycle identification (Hodrick-Prescott filter)
#   & Normalisation

fileLogs = open(os.path.join(outputDir, country + '_fileLogs_rsTransformation.txt'), 'w')
rs_SA_HP_norm = pipelineTransformations(rs, savePlots = outputDir, saveLogs = fileLogs)
fileLogs.close()


# 2.2) INDIVIDUAL INDICATORS

# 2.2a) Priority list of OECD available measures

priorityList = ['NCML'
                , 'ML'
                , 'CXML'
                , 'ST'
                , 'NCCU'
                , 'CXCU'
                , 'IXOB'
                , 'NCMLSA'
                , 'MLSA'
                , 'CXMLSA'
                , 'STSA'
                , 'NCCUSA'
                , 'CXCUSA'
                , 'IXOBSA'
                , 'IXNSA'
                , 'GP'
                , 'GY']

if data_adj.shape[0] > 0:
    
    data = getOnlyBestMeasure(df = data_adj, priorityList = priorityList)
    data = getRidOfMultiindex(df = data)
    data = getIndexAsDate(data)


# 2.2b) Seasonal adjustment, outlier filtering and short-term prediction
#   & Cycle identification (Hodrick-Prescott filter)
#   & Normalisation

fileLogs = open(os.path.join(outputDir, 'fileLogs_dataTransformation.txt'), 'w')
data_SA_HP_norm = pipelineTransformations(df = data, savePlots = outputDir, saveLogs = fileLogs, createInverse = True) 
fileLogs.close()


# 3) TURNING-POINT DETECTION (Bry-Boschan algorithm)

# 3.1) REFERENCE SERIES

fileLogs = open(os.path.join(outputDir, country + '_fileLogs_rsEvaluation.txt'), 'w')
rs_ind_turningPoints = pipelineTPDetection(rs_SA_HP_norm, savePlots = outputDir, saveLogs = fileLogs)
fileLogs.close()
    

# 3.2) INDIVIDUAL INDICATORS

fileLogs = open(os.path.join(outputDir, 'fileLogs_dataEvaluation.txt'), 'w')
data_ind_turningPoints = pipelineTPDetection(df = data_SA_HP_norm, origColumns = list(data.columns), savePlots = outputDir, saveLogs = fileLogs)
fileLogs.close()


# 4) TURNING-POINTS MATCHING

data_ind_extOrd, data_ind_time, data_ind_missing, data_ind_missingEarly, data_ind_extra = pipelineTPMatching(df1 = rs_SA_HP_norm, df2 = data_SA_HP_norm, ind1 = rs_ind_turningPoints, ind2 = data_ind_turningPoints, savePlots = outputDir, nameSuffix = '_06_matching' + '_rs' + country)


# 5) EVALUATION

data_totalEval, data_selectedEval, data_selectedCol = pipelineEvaluation(df1 = rs_SA_HP_norm, df2 = data_SA_HP_norm, missing = data_ind_missing, missingEarly = data_ind_missingEarly, extra = data_ind_extra, time = data_ind_time, maxInd = 15)


# 6) AGGREGATION & FINAL EVALUATION 

# 6a) CLI construction

agg_cMat = data_SA_HP_norm.loc[:, data_selectedCol] # value of the de-trended, smoothed and normalised component

CLI = pipelineCreateCLI(agg_cMat).rename(columns = {'CLI': country + '_CLI'})

compareTwoSeries(CLI, rs_SA_HP_norm)


# 6b) CLI turning points

fileLogs = open(os.path.join(outputDir, country + '_fileLogs_CLIEvaluation.txt'), 'w')
CLI_ind_turningPoints = pipelineTPDetection(CLI, savePlots = outputDir, saveLogs = fileLogs)
fileLogs.close()


# 6c) Match turning points

CLI_ind_extOrd, CLI_ind_time, CLI_ind_missing, CLI_ind_missingEarly, CLI_ind_extra = pipelineTPMatching(df1 = rs_SA_HP_norm, df2 = CLI, ind1 = rs_ind_turningPoints, ind2 = CLI_ind_turningPoints, savePlots = outputDir, nameSuffix = '_06_matching' + '_rs' + country, bw = bw)


# 6d) Basic characteristics
    
CLI_eval = pipelineEvaluation(df1 = rs_SA_HP_norm, df2 = CLI, missing = CLI_ind_missing, missingEarly = CLI_ind_missingEarly, extra = CLI_ind_extra, time = CLI_ind_time, evalOnly = True)
