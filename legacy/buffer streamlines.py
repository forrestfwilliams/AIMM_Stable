##Creator: Forrest Williams
##Contact: 4restwilliams@gmail.com
##Date: 1/2/18
##Python: 3.6.5
##Step: 3
##Purpose: Extract values from NDWI rasters within a buffered region around a channel, with
##  the polygon width equal to twice the channel width

#Load packages
import arcpy
import os
import time
#import skimage.filters as fil

arcpy.CheckOutExtension('Spatial')
from arcpy.sa import *

#Setup
name = 'hardin_widthbuff_no2'
cwd = 'C:\\Users\\forrestw\\Documents\\AIMM_tomer_6419'
os.chdir(cwd)
arcpy.env.workspace = cwd
arcpy.env.overwriteOutput = True

start = time.time()

order = [0,1,2,3,4,5]
order_buff = [0, 0, 0, 15, 24, 47]
#order_buff = [x*2 for x in order_buff]
waterways = 'hardin_centerlines.shp'
arcpy.AddField_management(waterways, 'buffer', 'FLOAT')
 
cursor = arcpy.da.UpdateCursor(waterways, ['Strm_order', 'buffer'])
for row in cursor:
    loc = order.index(row[0])
    row[1] = order_buff[loc]
    cursor.updateRow(row)
del cursor
  
ww_buff_frag = arcpy.Buffer_analysis(waterways, name+'_frag.shp', 'buffer')
ww_buff = arcpy.Dissolve_management(ww_buff_frag, name+'.shp')
print('vector done')

ww_mask = arcpy.PolygonToRaster_conversion(ww_buff, 'FID', name+'.tif', '','', 0.61)

end = time.time()
print(end-start)