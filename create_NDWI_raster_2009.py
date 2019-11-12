##Creator: Forrest Williams
##Contact: 4restwilliams@gmail.com
##Date: 12/20/18
##Python: 3.6.5
##Step: 1
##Purpose: Calucalte NDWI index for 2009 aerial photos on the county level
##Note: This script works with arcpro, but not with arcmap 10 or earlier
##  there is a bug that doesn't allow arcpy to access bands of a raster in earlier versions

#Load packages and set up initial conditions
import arcpy
import os
import time
arcpy.CheckOutExtension('Spatial')
from arcpy.sa import *
arcpy.env.overwriteOutput = True
arcpy.env.pyramid = 'NONE'
sr = arcpy.SpatialReference(26915) #this is NAD 83 UTM Zone 15 N

cwd = 'C:\\Users\\forrestw\\Documents\\ndwi_timing'
arcpy.env.workspace = cwd

counties = ['hardin8']
#montgomery
for county in counties:
    #Define path variables
    #county = 'audubon'
    year = '2009'
    print(county)
    print(year)

    start = time.time()
    #Define which bands correspond to Near-Infrared and Green
    #2009: nir = 1, g = 2
    #2002: nir = 1, g = 3
    g_band = '2'
    nir_band = '1'
    ras = '2009_CIR_airphotos_42.sid'

    #Raster bands can be stored as raster\\Layer_x, or raster\\Band_x, so you have to check both
    try:
        ext = 'Layer_'
        nir = arcpy.Raster(os.path.join(ras, ext+nir_band))
        green = arcpy.Raster(os.path.join(ras, ext+g_band))
    except:
        ext = 'Band_'
        nir = arcpy.Raster(os.path.join(ras, ext+nir_band))
        green = arcpy.Raster(os.path.join(ras, ext+g_band))
    print('loaded')

    #Caluclate Normalized Difference Water Index
    ndwi = (green - nir)/(green + nir) #funny how this only takes one line
    ndwi_8bit = Int((ndwi + 1)*127)
    #ndwi_16bit = Int((ndwi + 1)*32767)
    print('calculated')

    #Save file, this is what takes most of the time
    #ndwi.save(county+'_'+year+'.tif')
    out = arcpy.CopyRaster_management(ndwi_8bit, county+'_'+year+'.tif', '', '', 255, '', '', '8_BIT_UNSIGNED', 'NONE')
    #arcpy.CopyRaster_management(ndwi_16bit, county+'_'+year+'.tif', '', '', 65535, '', '', '16_BIT_UNSIGNED', 'NONE')
    print('saved')
    end = time.time()
    print(end - start)
    print('\n')
    #Put things back after we're done
    #arcpy.CheckInExtension('Spatial')
