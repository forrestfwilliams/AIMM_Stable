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
ww = os.path.join(root, 'watershed', 'nish_order.shp')
countyNish = os.path.join(root, 'watershed', 'county_nish.shp')
os.chdir(cwd)
arcpy.env.workspace = cwd

start = time.time()

orders = [3,4,5,6,7]
counties = ['adair', 'audubon', 'carroll', 'cass', 'crawford',
            'fremont', 'guthrie', 'mills', 'montgomery',
            'page', 'pottawattamie', 'shelby']
counties.remove('crawford')

for county in counties:
    print(county)
    pol ='{}_pol.shp'.format(county)
    bound = arcpy.MakeFeatureLayer_management(countyNish, 'counties')
    arcpy.SelectLayerByAttribute_management(bound, 'NEW_SELECTION',
                                            "COUNTY = '{}'".format(county.capitalize()))
    arcpy.Clip_analysis(pol, bound, os.path.join('all', '{}_clip.shp'.format(county)))

clipped = [os.path.join('all', '{}_clip.shp'.format(x)) for x in counties]
arcpy.Merge_management(clipped, os.path.join('all', 'all_pol.shp'))

cwd = os.path.join(cwd,'all')
os.chdir(cwd)
arcpy.env.workspace = cwd

pol = 'all_pol.shp'
arcpy.AddField_management(pol, 'StrmOrder', 'INTEGER')
polLyr = arcpy.MakeFeatureLayer_management(pol, 'polygon')
wwLyr = arcpy.MakeFeatureLayer_management(ww, 'ww')

for order in orders:
    print(order)
    arcpy.SelectLayerByAttribute_management(wwLyr, 'NEW_SELECTION', "Strm_order = {}".format(order))
    arcpy.SelectLayerByLocation_management(polLyr, 'INTERSECT', wwLyr)

    cursor = arcpy.da.UpdateCursor(polLyr, ['StrmOrder'])
    for row in cursor:
        row[0] = order
        cursor.updateRow(row)
    del cursor

polLyr = arcpy.SelectLayerByAttribute_management(polLyr, 'NEW_SELECTION', "hdiff <> 0")
arcpy.Copy_management('polygon', 'noZero.shp')
