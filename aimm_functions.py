#Load packages
import arcpy
import numpy as np
import pandas as pd
import skimage
import random
arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True
arcpy.env.pyramid = 'NONE'
from arcpy.sa import *

# Extract values from raster then determine land/water threshold value using Li's entropy threshold
# Raster is read in by block to prevent memory usage error
def calc_thresh(ndwi, mask, size, max_val):    
    # Clip Raster to stream corridor
    ras = ndwi + mask
    
    # Initialize empty array that will contain filtered values
    arr = np.array(np.zeros(1), dtype=np.uint8)
    
    # Set block size for raster reading
    blocksize = 248
    
    # Read and filter raster by block
    for x in range(0, ras.width, blocksize):
        for y in range(0, ras.height, blocksize):
    
            # Lower left coordinate of block (in map units)
            mx = ras.extent.XMin + x * ras.meanCellWidth
            my = ras.extent.YMin + y * ras.meanCellHeight
            
            # Upper right coordinate of block (in cells)
            lx = min([x + blocksize, ras.width])
            ly = min([y + blocksize, ras.height])
            #   noting that (x, y) is the lower left coordinate (in cells)
    
            # Extract data block
            flat = arcpy.RasterToNumPyArray(ras, arcpy.Point(mx, my), lx-x, ly-y).flatten()
            
            # Remove NODATA values
            flat_filt = flat[(flat > 0) & (flat < max_val)]
            
            # Only blocks that have non-NODATA values will be added to final array
            if flat_filt.shape[0] > 0:
                arr = np.append(arr, flat_filt)
    
    # Determine sample size for threshold analysis
    # The full dataset is not used due to computational limitations
    samp_size = min(arr.shape[0], size)
    
    # Initialize while loop
    t_list = []
    n = 0
    
    # Perform 50 iterations of thresholding
    while n <= 50:
        # Choose a random subset of raster values as training data for thresholding
        vals = np.random.choice(arr, int(samp_size), False)
        
        # Use Li's Entropy Threshold to determin
        thresh = skimage.filters.threshold_li(vals)
        
        # Append threshold to threshold list
        t_list.append(thresh)
        n += 1

    # Take median of list and convert threshold to integer
    thresh = int(np.ceil(np.median(t_list)) - 1)
    print('size = '+str(arr.shape[0]))
    
    # Remove unused variables
    del ras, blocksize, arr, mx, my, lx, ly, flat, flat_filt
    return([thresh, vals, t_list])

# Morphological opening
def opening(ras, val, n = 1):
    out = Expand(Shrink(ras, n, val), n, val)
    return(out)

# Morphological closing
def closing(ras, val, n = 1):
    out = Shrink(Expand(ras, n, val), n, val)
    return(out)

# Clean Classified NDWI image using morpological operations
def morpho_trim_old(in_ras, val, min_size):
    # Perform two morphological closings followed by one opening
    
    morpho = closing(in_ras, val, 2)
    #morpho = opening(cl, val, 2)
    
    # Reomve pixel zones that are smaller than the minimum size
    # Look at changing 0 to 1 AND 1 to 0 if below threshold
    rg = RegionGroup(morpho, '', '', 'NO_LINK')
    trimmed = Con(rg, morpho, 0, 'Count > '+str(min_size))
    
    # Remove unused variables
    #del ex_one, shrink, ex_two, rg
    return(trimmed)
    
def morpho_trim(in_ras, val, min_size):
    # Perform two morphological closings followed by one opening
    morpho = closing(in_ras, val, 1)#2
    # Reomve pixel zones that are smaller than the minimum size
    # Look at changing 0 to 1 AND 1 to 0 if below threshold
    rg = RegionGroup(morpho, '', '', 'NO_LINK')
    trimmed = Con(rg, morpho, Con(morpho, 0, val, 'Value = '+str(val)), 'Count > '+str(min_size))
    
    # Remove unused variables
    del rg, morpho
    return(trimmed)
    
def morpho_trim2(in_ras, val, min_size):
    # Perform two morphological closings followed by one opening
    morpho = closing(in_ras, val, 1)#2
    # Reomve pixel zones that are smaller than the minimum size
    # Look at changing 0 to 1 AND 1 to 0 if below threshold
    rg = RegionGroup(morpho, '', '', 'NO_LINK')
    trimmed = Con(rg, morpho, Con(morpho, 0, val, 'Value = '+str(val)), 'Count > '+str(min_size))
    
    # Remove unused variables
    del rg, morpho
    return(trimmed)

# Clean change detection raster using spatial relationships with channel zones
def proximity_trim(in_ras):
    # Create raster where stable channel zones are represented by 0 and expand it by 1 pixel
    water = Con(in_ras, 0, 1, 'Value = 3')
    
    water_expand = Expand(water, 1, 0)
    
    # Create regions from change detection raster
    groups = RegionGroup(in_ras, '', '', 'NO_LINK')
    
    # Determine which regions touch a channel region
    intersect = ZonalStatistics(groups, 'Value', water_expand * groups, 'MINIMUM', 'DATA')
    
    #intersect = ZonalStatistics(groups, 'Value', water * groups, 'MINIMUM', 'DATA')
    
    # Change zone values based on their proximity to a channel zone
    land_change = Con(intersect, in_ras, 2, 'Value = 0')
    erd_dep_change = Con(intersect, in_ras, 0, 'Value = 0')
    
    # Merge zone reclassifications
    land_addition = Con(in_ras, land_change, in_ras, 'Value = 0')
    merge = Con(land_addition, erd_dep_change, land_addition, 'Value = 1 OR Value = 2')

    # Remove unused variables
    del water, water_expand, groups, intersect, land_change, erd_dep_change, land_addition
    return(merge)

# Convert all szones that don't touch the channel mask to land zones
def channel_intersect(in_ras, channel):
    # Create groups by zone
    groups = RegionGroup(in_ras, '', '', 'NO_LINK')
    
    # Determine which regions touch a channel region
    intersect = ZonalStatistics(groups, 'Value', groups * IsNull(channel), 'MINIMUM', 'DATA')
    
    # Conver zones that do not touch the channel mask to land
    out_ras = Con(intersect, in_ras, 0, 'Value = 0')
    
    # Remove unused variables
    del groups, intersect
    return(out_ras)

# Remove erosion and deposition polygons that don't meet size and width criteria
def filter_pols(pol, name):
    # Inward buffer polygons by 2 m
    pol_in = arcpy.Buffer_analysis(pol, 'pol_in.shp', '-2 METERS')
    
    # Calculate geomtric attributes
    arcpy.CalculateGeometryAttributes_management(pol_in, [['area','AREA'], 
                                                  ['perim', 'PERIMETER_LENGTH']],
                                                 'METERS', 'SQUARE_METERS')
    
    # Calculate area to perimeter ratio and remove thin polygons
    cursor = arcpy.da.UpdateCursor(pol_in, ['area', 'perim'])
    for row in cursor:
        if row[0]/row[1] < 0.5:
            cursor.deleteRow()
    
    pol_out = arcpy.CopyFeatures_management(pol_in, name+'_filt.shp')
    
    # Remove unused variables
    del cursor, pol_in
    return(pol_out)

# Calculate height of eroding banks using several methods
def erosion_hdiff(pol, ras, dem, name, method1, method2):
    # Select erosion polygons
    pol_fl = arcpy.MakeFeatureLayer_management(pol, 'pol_fl')
    pol_erd_sel = arcpy.SelectLayerByAttribute_management(pol_fl, '', 'gridcode = 2')
    
    # If method is tomer, buffer polygons out 5 m
    if method1 == 'tomer':
        pol_erd = arcpy.Buffer_analysis(pol_erd_sel, name+'_erd_pol.shp', '5 METERS')
    elif method1 == 'normal':
        pol_erd = arcpy.CopyFeatures_management(pol_erd_sel, name+'_erd_pol.shp')
    
    # Calcuclate bank height with chosen method
    if method2 == 'med_diff':
        # Clip DEM to land or channel zones
        dem_land = Con(ras, dem, '', 'Value = 0 OR Value = 1')
        dem_water = Con(ras, dem, '', 'Value = 2 OR Value = 3')
        
        # Calculate median elevation of land zones surrounding erosional zones
        land =   pd.DataFrame(
                    arcpy.da.TableToNumPyArray(
                    ZonalStatisticsAsTable(pol_erd, 'Id', dem_land, 'land_dem', 'DATA', 'MEDIAN'), ['ID', 'MEDIAN']))
        
        # Calculate median elevation of channel zones surrounding erosional zones
        water =  pd.DataFrame(
                    arcpy.da.TableToNumPyArray(
                    ZonalStatisticsAsTable(pol_erd, 'Id', dem_water, 'water_dem', 'DATA', 'MEDIAN'), ['ID', 'MEDIAN']))
        
        # Find the difference between the median land and channel elevation for each erosion polygon
        erosion = land.join(water.set_index('ID'), on = 'ID', how = 'inner', lsuffix = '_L', rsuffix = '_W')
        erosion = erosion.assign(hdiff = erosion.MEDIAN_W - erosion.MEDIAN_L)
        
        # Remove unused variables
        del dem_land, dem_water, land, water
    elif method2 == 'sd4':
        # Determine the standard deviation of elevation values within each erosion polygon
        erosion =   pd.DataFrame(
                    arcpy.da.TableToNumPyArray(
                    ZonalStatisticsAsTable(pol_erd, 'Id', dem, 'hdiff_erd', 'DATA', 'STD'), ['ID', 'STD']))
        
        # Rename columns and multiply standard deviation by 4 (in order to capture 95% of elevation variation)
        erosion.columns = ['ID', 'hdiff']
        erosion.hdiff *=-4
        
    elif method2 == 'range':
        # Determine the standard deviation of elevation values within each erosion polygon
        erosion =   pd.DataFrame(
                    arcpy.da.TableToNumPyArray(
                    ZonalStatisticsAsTable(pol_erd, 'Id', dem, 'hdiff_erd', 'DATA', 'RANGE'), ['ID', 'RANGE']))
        
        # Rename columns and multiply standard deviation by 4 (in order to capture 95% of elevation variation)
        erosion.columns = ['ID', 'hdiff']
        erosion.hdiff *=-1
        
    # Remove unused variables
    del pol_fl, pol_erd_sel, pol_erd
    
    # Return table of polygon id and bank height
    return(erosion)

# Calculate height of depositional areas
def deposition_hdiff(pol, dem, name, method1, method2):
    # Select deposition polygons
    pol_fl = arcpy.MakeFeatureLayer_management(pol, 'pol_fl')
    pol_dep_sel = arcpy.SelectLayerByAttribute_management(pol_fl, '', 'gridcode = 1')
    
    # If method is tomer, buffer polygons out 2 m
    if method1 == 'tomer':
        pol_dep = arcpy.Buffer_analysis(pol_dep_sel, name+'_dep.shp', '2 METERS')
    elif method1 == 'normal':
        pol_dep = arcpy.CopyFeatures_management(pol_dep_sel, name+'_dep.shp')
    
    # Determine minimum elevation value within deposition polygon
    min_ras = ZonalStatistics(pol_dep, 'Id', dem, 'MINIMUM', 'DATA')
    
    # Calculate the average elevation difference between minimum elevation and deposition polygon
    average_stat = method2
    
    hdiff_dep = dem - min_ras
    deposition =    pd.DataFrame(
                    arcpy.da.TableToNumPyArray(
                    ZonalStatisticsAsTable(pol_dep, 'Id', hdiff_dep, 'hdiff_dep', 'DATA', average_stat), ['ID', average_stat]))
    deposition.columns = ['ID', 'hdiff']
    
    # Remove unused variables
    del pol_fl, pol_dep_sel, pol_dep, min_ras, hdiff_dep
    
    # Return table of polygon id and bank height
    return(deposition)

# Append bank height table to polygon attribute table using ID field and calculate volume
def merge_pol_hdiff(pol, hdiff):
    # Get IDs
    ids = list(hdiff['ID'])
    
    # Update hdiff field and calculate area
    cursor = arcpy.da.UpdateCursor(pol, ['Id', 'hdiff', 'area', 'vol_chg'])
    for row in cursor:
        if row[0] in ids:
            hdiff_row = hdiff.loc[hdiff['ID'] == row[0]]
            value = hdiff_row.iloc[0][1]
            row[1] = value/100 # hdiff is divided by 100 to convert from cm to m
        row[3] = row[1]*row[2]
        cursor.updateRow(row)
    
    # Remove unused variables
    del cursor, ids, value, hdiff_row, row
    
    # Return polygon
    return(pol)

def calculate_hdiff_tomer(name, ras_full, dem_full, mask, tomer):
    ras = ras_full + mask
    #dem = dem_full + mask
    dem = dem_full
    ras_filt = Con(ras, ras, '', 'Value = 1 OR Value = 2')
    pol = arcpy.RasterToPolygon_conversion(ras_filt, name+'_pol.shp', 'NO_SIMPLIFY', 'VALUE')
    arcpy.AddField_management(pol, 'area', 'FLOAT')
    arcpy.AddField_management(pol, 'perim', 'FLOAT')
    arcpy.AddField_management(pol, 'hdiff', 'FLOAT')
    arcpy.AddField_management(pol, 'vol_chg', 'FLOAT')

    if tomer == True:
        pol_in = arcpy.Buffer_analysis(pol, 'pol_in2.shp', '-2 METERS')
        pol_fl = arcpy.MakeFeatureLayer_management(pol_in, 'pol_ft')
        arcpy.CalculateGeometryAttributes_management(pol_fl,
                                                     [['area','AREA'], ['perim', 'PERIMETER_LENGTH']],
                                                     'METERS', 'SQUARE_METERS')
        cursor = arcpy.da.UpdateCursor(pol_fl, ['area', 'perim'])
        for row in cursor:
            if row[0]/row[1] < 0.5:
                cursor.deleteRow()
        del cursor
        
        pol_out = arcpy.CopyFeatures_management(pol_fl, name+'_filt.shp')
        pol_fl = arcpy.MakeFeatureLayer_management(pol_out, 'pol_ft')
        pol_erd = arcpy.SelectLayerByAttribute_management(pol_fl, '', 'gridcode = 2')
        pol_erd_buff = arcpy.Buffer_analysis(pol_erd, name+'_erd_pol.shp', '5 METERS')
        pol_dep = arcpy.SelectLayerByAttribute_management(pol_fl, '', 'gridcode = 1')
        pol_dep_buff = arcpy.Buffer_analysis(pol_dep, name+'_dep_pol.shp', '2 METERS')
        
    elif tomer == False:
        pol_out = pol
        arcpy.CalculateField_management(pol_out, 'area', "!SHAPE.AREA!", 'PYTHON')
        pol_fl = arcpy.MakeFeatureLayer_management(pol_out, 'pol')
        pol_erd = arcpy.SelectLayerByAttribute_management(pol_fl, '', 'gridcode = 2')
        pol_erd_buff = arcpy.Buffer_analysis(pol_erd, 'erd_pol.shp', '3 METERS')
        pol_dep = arcpy.SelectLayerByAttribute_management(pol_fl, '', 'gridcode = 1')
        pol_dep_buff = arcpy.CopyFeatures_management(pol_dep, 'dep_pol.shp')

    dem_land = Con(ras, dem, '', 'Value = 0 OR Value = 1')
    dem_water = Con(ras, dem, '', 'Value = 2 OR Value = 3')

    land =   pd.DataFrame(
                arcpy.da.TableToNumPyArray(
                ZonalStatisticsAsTable(pol_erd_buff, 'Id', dem_land, 'land_dem', 'DATA', 'MEDIAN'), ['ID', 'MEDIAN']))
    water =  pd.DataFrame(
                arcpy.da.TableToNumPyArray(
                ZonalStatisticsAsTable(pol_erd_buff, 'Id', dem_water, 'water_dem', 'DATA', 'MEDIAN'), ['ID', 'MEDIAN']))

    erosion = land.join(water.set_index('ID'), on = 'ID', how = 'inner', lsuffix = '_L', rsuffix = '_W')
    erosion = erosion.assign(hdiff = erosion.MEDIAN_W - erosion.MEDIAN_L)

    min_ras = ZonalStatistics(pol_dep_buff, 'Id', dem, 'MINIMUM', 'DATA')
    hdiff_dep = dem - min_ras
    deposition =    pd.DataFrame(
                    arcpy.da.TableToNumPyArray(
                    ZonalStatisticsAsTable(pol_dep_buff, 'Id', hdiff_dep, 'hdiff_dep', 'DATA', 'MEAN'), ['ID', 'MEAN']))
    deposition.columns = ['ID', 'hdiff']
    hdiff = deposition.append(erosion[['ID', 'hdiff']])
    hdiff.to_csv(name+'hdiff.csv')

    ids = list(hdiff['ID'])
    cursor = arcpy.da.UpdateCursor(pol_out, ['Id', 'hdiff', 'area', 'vol_chg'])
    for row in cursor:
        if row[0] in ids:
            hdiff_row = hdiff.loc[hdiff['ID'] == row[0]]
            value = hdiff_row.iloc[0][1]
            row[1] = value/100

        row[3] = row[1]*row[2]
        cursor.updateRow(row)
    del cursor

    return(pol_out)
