#Load packages
import arcpy
import os
import time
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import aimm_functions as aimm
arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True
arcpy.env.pyramid = 'NONE'
arcpy.env.cellSize = 'MAXOF'
from arcpy.sa import *

# Set working directory
cwd = 'C:\\AIMM\\nishnabotna\\output01242020'
os.chdir(cwd)
arcpy.env.workspace = cwd

counties = ['adair', 'audubon', 'carroll', 'cass', 'crawford',
            'fremont', 'guthrie', 'mills', 'montgomery',
            'page', 'pottawattamie', 'shelby']
# Load input data
name = 'adair'
dem = arcpy.Raster('C:\\AIMM\\nishnabotna\\dem\\adair.img')
thresh_mask = arcpy.Raster('C:\\AIMM\\nishnabotna\\watershed\\waterways_mask_current.tif')
clip_mask = arcpy.Raster('C:\\AIMM\\nishnabotna\\watershed\\waterways_mask_current.tif')
ndwi_old = arcpy.Raster('C:\\AIMM\\nishnabotna\\ndwi_09\\adair8_2009')
ndwi_new = arcpy.Raster('C:\\AIMM\\nishnabotna\\ndwi_18\\adair8_2018')

#```````````````````````````````````````````````````````````````#
# Set snap raster
arcpy.env.snapRaster = ndwi_old

# Start timing
start = time.time()
print('starting '+name)
print(datetime.datetime.now())

# Set cell size option to minimum of rasters and calculate threshold for first image
arcpy.env.cellSize = 'MINOF'
t_old = aimm.calc_thresh(ndwi_old, thresh_mask, 5e6, 255)
print(t_old[0])

# Create and save histogram of NDWI values
hist1 = plt.hist(t_old[1], bins = 255)
plt.savefig(name+'_2002.jpg')
plt.close()

# Calculate threshold for second image
t_new = aimm.calc_thresh(ndwi_new, thresh_mask, 5e6, 255)
print(t_new[0])

# Create and save histogram of NDWI values
hist2 = plt.hist(t_new[1], bins = 255)
plt.savefig(name+'_2009.jpg')
plt.close()

print('thresholds selected')
print(datetime.datetime.now())
del hist1, hist2

# Create binary rasters of channel location by 
# Reclassify land pixels to 0 and water/channel pixels to 1 for old image and 2 for new image
rclold = Reclassify(ndwi_old, "Value", RemapRange([[0,t_old[0],0],[t_old[0],255,1]]))
rclnew = Reclassify(ndwi_new, "Value", RemapRange([[0,t_new[0],0],[t_new[0],255,2]]))

# Clean Classified NDWI images using morpological operations
rclold2 = aimm.morpho_trim(rclold, 1, 10) #10
rclnew2 = aimm.morpho_trim(rclnew, 2, 10) #10

# Save images
rclold2.save(name+'_rcold.tif')
rclnew2.save(name+'_rcnew.tif')

print('reclassed')
print(datetime.datetime.now())
del rclold, rclnew, ndwi_old, ndwi_new

# Change cell size setting and overlay binary channel rasters
# In overlay raster Stable land = 0, Deposition = 1, Erosion = 2, and Stable Channel = 3
arcpy.env.cellSize = 'MAXOF'
overlay = rclold2 + rclnew2
overlay.save(name+'_raw.tif')

# Convert all szones that don't touch the channel mask to land zones
overlay_clean = aimm.channel_intersect(overlay, clip_mask)

# Clean change detection raster using spatial relationships with channel zones
ras = aimm.proximity_trim(overlay_clean)
end = time.time()
print(end - start)
# Save cleaned overlay raster and set as snap raster
ras.save(name + '_final.tif')
arcpy.env.snapRaster = ras
arcpy.env.cellSize = 'MINOF'

print('migration raster created')
print(datetime.datetime.now())
del overlay, overlay_clean

end = time.time()
print(end -start)
# Convert erosion and deposition zones to polygons
ras_filt = Con(ras, ras, '', 'Value = 1 OR Value = 2')
pol = arcpy.RasterToPolygon_conversion(ras_filt, name+'_pol.shp', 'NO_SIMPLIFY', 'VALUE')

# Add fields to polygos
arcpy.AddField_management(pol, 'area', 'FLOAT')
arcpy.AddField_management(pol, 'perim', 'FLOAT')
arcpy.AddField_management(pol, 'hdiff', 'FLOAT')
arcpy.AddField_management(pol, 'vol_chg', 'FLOAT')

# Calculate geomtric attributes
arcpy.CalculateGeometryAttributes_management(pol, [['area','AREA'], 
                                                  ['perim', 'PERIMETER_LENGTH']],
                                                 'METERS', 'SQUARE_METERS')

# Remove erosion and deposition polygons that don't meet size and width criteria
#pol = aimm.filter_pols(pol, name)

# Calculate height of eroding banks using several methods
erosion = aimm.erosion_hdiff(pol, ras, dem, name, 'normal', 'sd4')

# Calculate height of depositional areas
deposition = aimm.deposition_hdiff(pol, dem, name, 'normal', 'median')

# Combine height tables for erosion and deposition
hdiff = deposition.append(erosion[['ID', 'hdiff']])

# Append bank height table to polygon attribute table using ID field and calculate volume
final_pol = aimm.merge_pol_hdiff(pol, hdiff)

print('polygons done')
print(datetime.datetime.now())
end = time.time()

# Save threshold and timing information for each iteration
df = pd.DataFrame(columns=['Name', 'Threshold 1', 'Threshold 2', 'Time'])
data = {'Name': [name], 'Threshold 1': [t_old[0]], 'Threshold 2': [t_new[0]], 'Time': [end-start]}
df = df.append(pd.DataFrame(data))
df.to_csv(name+'_results.csv')

print('finished '+name)
print(datetime.datetime.now())
print((end - start)/60)
print('#~~~~~~~~~~~~~~~~~~~~~~~~~~~#\n')
del start, end, data, name

print('completely done!')
