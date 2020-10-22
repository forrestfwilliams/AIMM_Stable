
#Load packages
import arcpy
import os
import glob
import time
import datetime
import numpy as np
import pandas as pd
arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True
from arcpy.sa import *

root = 'C:\\AIMM\\nishnabotna'
cwd = os.path.join(root, 'outputMaskChange')
suffix = '*_pol.shp'
ww = os.path.join(root, 'watershed', 'nish_waterways.shp')
countyNish = os.path.join(root, 'watershed', 'county_nish.shp')
os.chdir(cwd)
arcpy.env.workspace = cwd

start = time.time()
pols = glob.glob(suffix, recursive = True)
counties = ['adair', 'audubon', 'carroll', 'cass', 'crawford',
            'fremont', 'guthrie', 'mills', 'montgomery',
            'page', 'pottawattamie', 'shelby']
counties.remove('crawford')

##for county in counties:
##    print(county)
##    pol ='{}_pol.shp'.format(county)
##    bound = arcpy.MakeFeatureLayer_management(countyNish, 'counties')
##    arcpy.SelectLayerByAttribute_management(bound, 'NEW_SELECTION',
##                                            "COUNTY = '{}'".format(county.capitalize()))
##    arcpy.Clip_analysis(pol, bound, os.path.join('all', '{}_clip.shp'.format(county)))

clipped = [os.path.join('all', '{}_clip.shp'.format(x)) for x in counties]
arcpy.Merge_management(clipped, os.path.join('all', 'all_pol.shp'))
##fm_hdiff = arcpy.FieldMap()
##fm_gridcode = arcpy.FieldMap()
##fms = arcpy.FieldMappings()
##for pol in pols:
##    fm_hdiff.addInputField(pol,'hdiff')
##    fm_gridcode.addInputField(pol,'gridcode')
##    
##fm_hdiff.mergeRule = 'Mean'
##fm_gridcode.mergeRule = 'First'
##
##fms.addFieldMap(fm_hdiff)
##fms.addFieldMap(fm_gridcode)
##
##all_pols = arcpy.Merge_management(pols, 'all_pols.shp', fms)
##all_pols = 'all_pols.shp'

##print('merge done')
##print(datetime.datetime.now())
##
##pols_lyr = arcpy.MakeFeatureLayer_management(all_pols, 'pols_lyr')
##arcpy.SelectLayerByLocation_management(pols_lyr, 'INTERSECT', ww_buff)
##pols_nish = arcpy.CopyFeatures_management(pols_lyr, 'pols_nish.shp')
##pols_nish = 'pols_nish.shp'
##
##print('selection done')
##print(datetime.datetime.now())
##
##arcpy.AddField_management(pols_nish, 'area', 'FLOAT')
##arcpy.AddField_management(pols_nish, 'vol_chg', 'FLOAT')
##
##arcpy.CalculateField_management(pols_nish, 'area', "!SHAPE.AREA!", 'PYTHON')
##
##cursor = arcpy.da.UpdateCursor(pols_nish, ['hdiff', 'area', 'vol_chg'])
##for row in cursor:
##    row[2] = (row[0]/100.0) * row[1]
##    cursor.updateRow(row)
##del cursor
##
##pols_nish = 'pols_nish.shp'
##pols_nish = arcpy.CopyFeatures_management(pols_nish, 'pols_nish_clean.shp')
##pols_nish = 'pols_nish_clean.shp'
##cursor =  arcpy.da.SearchCursor(pols_nish, ['gridcode', 'area', 'perim', 'vol_chg'])
##area = []
##perim = []
##for row in cursor:
####    if row[0] == 1:
####        row[2] = abs(row[2])
####    elif row[0] == 2:
####        row[2] = abs(row[2])*-1
##    area.append(row[1])
##    perim.append(row[2])
####    cursor.updateRow(row)
##del cursor
##
##thresh1 = np.percentile(area, 99.98)
##thresh2 = np.percentile(perim, 99.98)
##
##cursor =  arcpy.da.UpdateCursor(pols_nish, ['gridcode', 'area', 'perim', 'vol_chg'])
##deleted = 0
##for row in cursor:
##    if row[1] >= thresh1:
##        cursor.deleteRow()
##        deleted += 1
##    elif row[2] >= thresh2:
##        cursor.deleteRow()
##        deleted += 1 
##del cursor
##
##cursor =  arcpy.da.SearchCursor(pols_nish, ['gridcode', 'area', 'vol_chg'])     
##erd = []
##dep = []
##for row in cursor:
##    if row[0] == 1:
##        dep.append(row[2])
##    elif row[0] == 2:
##        erd.append(row[2])
##del cursor
##
##sum(dep)+sum(erd)
##
##print('script done')
##print(datetime.datetime.now())
##
##end = time.time()
##print(end- start)
