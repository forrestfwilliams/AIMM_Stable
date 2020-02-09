#Load packages
import arcpy
import os
import pandas as pd
arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True
from arcpy.sa import *

os.chdir('C:\\AIMM\\nishnabotna\\outputMaskChange\\all')

shp = 'cleaning.shp'

arr = arcpy.da.FeatureClassToNumPyArray(shp, ['gridcode', 'area', 'perim', 'hdiff', 'vol_chg', 'StrmOrder'])#
df = pd.DataFrame(arr)
df.to_csv('aimm.csv')
