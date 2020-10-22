# ArcPy Imports
import arcpy
from arcpy.sa import *

# Non-ArcPy imports
import os
import numpy as np
import pandas as pd
from skimage import filters
from datetime import datetime

# If ImportError occurs try installing skimage in ArcGIS Pro's conda command line:
# conda install -c anaconda scikit-image

"""
Function Usage Structure:

aimm.pyt
    |---Toolbox
    |   
    |---NDWI
    |   |---ndwi_function
    |   
    |---threshold
    |   |---threshold_function
    |   
    |---river
    |   |---river_function
    |       |---closing
    |   
    |---migration
    |   |---migration_function
    |   
    |---volume
    |   |---volume_function
    |       |---erosion_hdiff
    |       |---deposition_hdiff
    |   
    |---AIMM
        |---ndwi_function
        |---threshold_function
        |---river_function
            |---closing
        |---migration_function
        |---volume_function
            |---erosion_hdiff
            |---deposition_hdiff
"""



## Helper Functions
# Morphological Opening
def opening(ras, val, n = 1):
    out = Expand(Shrink(ras, n, val), n, val)
    return(out)

# Morphological Closing
def closing(ras, val, n = 1):
    out = Shrink(Expand(ras, n, val), n, val)
    return(out)

# Calculate height of eroding banks using several methods
def erosion_hdiff(pol, ras, dem, method1, method2):
    # Select erosion polygons
    pol_fl = arcpy.MakeFeatureLayer_management(pol, 'pol_fl')
    pol_erd_sel = arcpy.SelectLayerByAttribute_management(pol_fl, '', 'gridcode = 2')
    
    # If method is tomer, buffer polygons out 5 m
    if method1 == 'tomer':
        pol_erd = arcpy.Buffer_analysis(pol_erd_sel, 'erd.shp', '5 METERS')
    elif method1 == 'normal':
        pol_erd = arcpy.CopyFeatures_management(pol_erd_sel, 'erd.shp')
    
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
    
    # Return table of polygon id and bank height
    return(erosion)

# Calculate height of depositional areas
def deposition_hdiff(pol, dem, method1, method2):
    # Select deposition polygons
    pol_fl = arcpy.MakeFeatureLayer_management(pol, 'pol_fl')
    pol_dep_sel = arcpy.SelectLayerByAttribute_management(pol_fl, '', 'gridcode = 1')
    
    # If method is tomer, buffer polygons out 2 m
    if method1 == 'tomer':
        pol_dep = arcpy.Buffer_analysis(pol_dep_sel, 'dep.shp', '2 METERS')
    elif method1 == 'normal':
        pol_dep = arcpy.CopyFeatures_management(pol_dep_sel, 'dep.shp')
    
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

## Tool functions
def ndwi_function(nir,green,output):
    # Calucate to NDWI
    ndwi = (green - nir)/(green + nir)

    # Convert to 8 bit number
    ndwi_8bit = Int((ndwi + 1)*126)

    arcpy.CopyRaster_management(ndwi_8bit, output, '', '', 255, '', '', '8_BIT_UNSIGNED', 'NONE')
    return

def threshold_function(ndwi,mask,nodata,output):
    # Clip Raster to stream corridor
    ras = ndwi * mask

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
            flat_filt = flat[(flat >= 0) & (flat <= 255) & (flat != nodata)]
            
            # Only blocks that have non-NODATA values will be added to final array
            if flat_filt.shape[0] > 0:
                arr = np.append(arr, flat_filt)

    # Determine sample size for threshold analysis
    # The full dataset is not used due to computational limitations
    samp_size = min(arr.shape[0], 1e6)

    # Initialize while loop
    t_list = []
    n = 0

    # Perform 10 iterations of thresholding
    while n <= 10:
        # Choose a random subset of raster values as training data for thresholding
        vals = np.random.choice(arr, int(samp_size), False)
        
        # Use Li's Entropy Threshold to determin
        thresh = filters.threshold_li(vals)
        
        # Append threshold to threshold list
        t_list.append(thresh)
        n += 1

    # Take median of list and convert threshold to integer
    thresh = int(np.ceil(np.median(t_list)) - 1)

    # Write to file
    lines = ['Category,Value\n',f'Time,{datetime.now()}\n',f'Raster,{ndwi.catalogPath}\n', f'Threshold,{thresh}']
    with open(output, "w") as f:
        for line in lines:
            f.write(line)
    return(thresh)

def river_function(ndwi,threshold,min_size,raster,output):
    water_value = {'Old Raster':1, 'New Raster':2}

    reclass = Reclassify(ndwi, "Value", RemapRange([[0,threshold,0],[threshold,255,water_value[raster]]]))
    # Perform one Morphological Closing
    morpho = closing(reclass, water_value[raster], 1)
    # Reomve pixel zones that are smaller than the minimum size
    # Look at changing 0 to 1 AND 1 to 0 if below threshold
    rg = RegionGroup(morpho, '', '', 'NO_LINK')
    trimmed = Con(rg, morpho, Con(morpho, 0, water_value[raster], 'Value = '+str(water_value[raster])), 'Count > '+str(min_size))
    trimmed.save(output)
    return

def migration_function(old,new,mask,output):
    # Overlay river rasters
    overlay = old + new

    # Create groups by zone
    groups = RegionGroup(overlay, '', '', 'NO_LINK')
    
    # Determine which regions touch a channel region
    intersect = ZonalStatistics(groups, 'Value', groups * IsNull(mask), 'MINIMUM', 'DATA')
    
    # Convert zones that do not touch the channel mask to land
    channel_masked = Con(intersect, overlay, 0, 'Value = 0')

    # Create raster where stable channel zones are represented by 0 and expand it by 1 pixel
    water = Con(channel_masked, 0, 1, 'Value = 3')
    
    water_expand = Expand(water, 1, 0)
    
    # Create regions from change detection raster
    groups = RegionGroup(channel_masked, '', '', 'NO_LINK')
    
    # Determine which regions touch a channel region
    intersect = ZonalStatistics(groups, 'Value', water_expand * groups, 'MINIMUM', 'DATA')
    
    # Change zone values based on their proximity to a channel zone
    land_change = Con(intersect, channel_masked, 2, 'Value = 0')
    erd_dep_change = Con(intersect, channel_masked, 0, 'Value = 0')
    
    # Merge zone reclassifications
    land_addition = Con(channel_masked, land_change, channel_masked, 'Value = 0')
    merge = Con(land_addition, erd_dep_change, land_addition, 'Value = 1 OR Value = 2')
    merge.save(output)
    return

def volume_function(migration,dem,scale,output):
    # Convert erosion and deposition zones to polygons
    ras_filt = Con(migration, migration, '', 'Value = 1 OR Value = 2')
    pol = arcpy.RasterToPolygon_conversion(ras_filt, output, 'NO_SIMPLIFY', 'VALUE')

    # Add fields to polygons
    arcpy.AddField_management(pol, 'area', 'FLOAT')
    arcpy.AddField_management(pol, 'perim', 'FLOAT')
    arcpy.AddField_management(pol, 'hdiff', 'FLOAT')
    arcpy.AddField_management(pol, 'vol_chg', 'FLOAT')

    # Calculate geomtric attributes
    arcpy.CalculateGeometryAttributes_management(pol, [['area','AREA'], 
                                            ['perim', 'PERIMETER_LENGTH']],
                                            'METERS', 'SQUARE_METERS')

    # Calculate height of eroding banks using several methods
    erosion = erosion_hdiff(pol, migration, dem, 'normal', 'sd4')

    # Calculate height of depositional areas
    deposition = deposition_hdiff(pol, dem, 'normal', 'median')

    # Combine height tables for erosion and deposition
    hdiff = deposition.append(erosion[['ID', 'hdiff']])

    # Get IDs
    ids = list(hdiff['ID'])
    
    # Update hdiff field and calculate area
    cursor = arcpy.da.UpdateCursor(pol, ['Id', 'hdiff', 'area', 'vol_chg'])
    for row in cursor:
        if row[0] in ids:
            hdiff_row = hdiff.loc[hdiff['ID'] == row[0]]
            value = hdiff_row.iloc[0][1]
            row[1] = value*scale # Used to change scale of elevation output
        row[3] = row[1]*row[2]
        if row[1] == 0:
            cursor.deleteRow()
        else:
            cursor.updateRow(row)
    return

## Tool Classes
class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [NDWI,threshold,river,migration,volume,AIMM]

class NDWI(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create NDWI Raster"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input Infrared Raster",
            name="nir",
            datatype=["DERasterDataset", "DERasterCatalog"],
            parameterType="Required",
            direction="Input")
        
        param1 = arcpy.Parameter(
            displayName="Input Green Raster",
            name="green",
            datatype=["DERasterDataset", "DERasterCatalog"],
            parameterType="Required",
            direction="Input")
        
        param2 = arcpy.Parameter(
            displayName="Output NDWI Raster",
            name="output",
            datatype=["DERasterDataset", "DERasterCatalog"],
            parameterType="Required",
            direction="Output")

        params = [param0,param1,param2]
        return params

    def execute(self, parameters, messages):
        """The source code of the tool."""
        arcpy.CheckOutExtension('Spatial')
        nir = arcpy.Raster(parameters[0].valueAsText)
        green = arcpy.Raster(parameters[1].valueAsText)
        output = parameters[2].valueAsText

        ndwi_function(nir,green,output)

        arcpy.CheckInExtension('Spatial')
        return

class threshold(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Compute Threshold"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input NDWI Raster",
            name="ndwi",
            datatype=["DERasterDataset", "DERasterCatalog"],
            parameterType="Required",
            direction="Input")
        
        param1 = arcpy.Parameter(
            displayName="Input River Classification Mask",
            name="mask",
            datatype=["DERasterDataset", "DERasterCatalog"],
            parameterType="Required",
            direction="Input")
        
        param2 = arcpy.Parameter(
            displayName="NoData Value",
            name="nodata",
            datatype=["GPLong"],
            parameterType="Required",
            direction="Input")
        
        param3 = arcpy.Parameter(
            displayName="Output Classification Text File",
            name="output",
            datatype=["DEFile"],
            parameterType="Required",
            direction="Output")
        # param3.filter.list = ["txt", "csv"] #Can't make this work
        
        params = [param0,param1,param2,param3]
        return params

    def execute(self, parameters, messages):
        """The source code of the tool."""
        arcpy.CheckOutExtension('Spatial')
        ndwi = arcpy.Raster(parameters[0].valueAsText)
        mask = arcpy.Raster(parameters[1].valueAsText)
        nodata =  int(parameters[2].valueAsText)
        output = parameters[3].valueAsText
       
        thresh = threshold_function(ndwi,mask,nodata,output)

        arcpy.AddMessage(f'Threshold is {thresh}')
 
        arcpy.CheckInExtension('Spatial')
        return

class river(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create River Raster"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input NDWI Raster",
            name="ndwi",
            datatype=["DERasterDataset", "DERasterCatalog"],
            parameterType="Required",
            direction="Input")
        
        param1 = arcpy.Parameter(
            displayName="Threshold Value",
            name="threshold",
            datatype=["GPLong"],
            parameterType="Required",
            direction="Input")
        
        param2 = arcpy.Parameter(
            displayName="Minimum Pixel Size of River Zone",
            name="pixel size",
            datatype=["GPLong"],
            parameterType="Required",
            direction="Input")
        param2.value = 10

        param3 = arcpy.Parameter(
            displayName="Old or New Raster?",
            name="val",
            datatype="String",
            parameterType="Required",
            direction="Input")
        param3.filter.list = ['Old Raster', 'New Raster']

        param4 = arcpy.Parameter(
            displayName="Output Binary River Raster",
            name="river",
            datatype=["DERasterDataset", "DERasterCatalog"],
            parameterType="Required",
            direction="Output")

        params = [param0,param1,param2,param3,param4]
        return params

    def execute(self, parameters, messages):
        """The source code of the tool."""
        arcpy.CheckOutExtension('Spatial')
        ndwi = arcpy.Raster(parameters[0].valueAsText)
        threshold = int(parameters[1].valueAsText)
        min_size = int(parameters[2].valueAsText)
        raster = parameters[3].valueAsText
        output = parameters[4].valueAsText

        river_function(ndwi,threshold,min_size,raster,output)

        arcpy.CheckInExtension('Spatial')
        return

class migration(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create Migration Raster"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input Old River Raster",
            name="old",
            datatype=["DERasterDataset", "DERasterCatalog"],
            parameterType="Required",
            direction="Input")
        
        param1 = arcpy.Parameter(
            displayName="Input New River Raster",
            name="new",
            datatype=["DERasterDataset", "DERasterCatalog"],
            parameterType="Required",
            direction="Input")
        
        param2 = arcpy.Parameter(
            displayName="Input River Corridor Mask",
            name="mask",
            datatype=["DERasterDataset", "DERasterCatalog"],
            parameterType="Required",
            direction="Input")
        
        param3 = arcpy.Parameter(
            displayName="Output Migration Raster",
            name="output",
            datatype=["DERasterDataset", "DERasterCatalog"],
            parameterType="Required",
            direction="Output")

        params = [param0,param1,param2,param3]
        return params

    def execute(self, parameters, messages):
        """The source code of the tool."""
        arcpy.CheckOutExtension('Spatial')
        old = arcpy.Raster(parameters[0].valueAsText)
        new = arcpy.Raster(parameters[1].valueAsText)
        mask = arcpy.Raster(parameters[2].valueAsText)
        output = parameters[3].valueAsText

        arcpy.env.cellSize = 'MAXOF'
        migration_function(old,new,mask,output)

        arcpy.CheckInExtension('Spatial')
        return

class volume(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Calcuate Volumes"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input Migration Raster",
            name="migration",
            datatype=["DERasterDataset", "DERasterCatalog"],
            parameterType="Required",
            direction="Input")
        
        param1 = arcpy.Parameter(
            displayName="Input DEM",
            name="dem",
            datatype=["DERasterDataset", "DERasterCatalog"],
            parameterType="Required",
            direction="Input")

        param2 = arcpy.Parameter(
            displayName="DEM Scale Value",
            name="scale",
            datatype=["GPDouble"],
            parameterType="Required",
            direction="Input")
        param2.value = 1
        
        param3 = arcpy.Parameter(
            displayName="Output Erosion and Deposition Polygons",
            name="output",
            datatype=["DEFeatureClass"],
            parameterType="Required",
            direction="Output")

        params = [param0,param1,param2,param3]
        return params


    def execute(self, parameters, messages):
        """The source code of the tool."""
        arcpy.CheckOutExtension('Spatial')

        migration = arcpy.Raster(parameters[0].valueAsText)
        dem = arcpy.Raster(parameters[1].valueAsText)
        scale = float(parameters[2].valueAsText)
        output = parameters[3].valueAsText
        arcpy.env.snapRaster = migration
        
        arcpy.env.cellSize = 'MINOF'
        volume_function(migration,dem,scale,output)
        arcpy.env.cellSize = 'MAXOF'

        arcpy.CheckInExtension('Spatial')
        return

class AIMM(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "AIMM"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input Old Infrared Raster",
            name="nirOld",
            datatype=["DERasterDataset", "DERasterCatalog"],
            parameterType="Required",
            direction="Input")
        
        param1 = arcpy.Parameter(
            displayName="Input Old Green Raster",
            name="greenOld",
            datatype=["DERasterDataset", "DERasterCatalog"],
            parameterType="Required",
            direction="Input")
        
        param2 = arcpy.Parameter(
            displayName="Input New Infrared Raster",
            name="nirNew",
            datatype=["DERasterDataset", "DERasterCatalog"],
            parameterType="Required",
            direction="Input")
        
        param3 = arcpy.Parameter(
            displayName="Input New Green Raster",
            name="greenNew",
            datatype=["DERasterDataset", "DERasterCatalog"],
            parameterType="Required",
            direction="Input")
        
        param4 = arcpy.Parameter(
            displayName="Input River Classification Mask",
            name="maskClassification",
            datatype=["DERasterDataset", "DERasterCatalog"],
            parameterType="Required",
            direction="Input")
        
        param5 = arcpy.Parameter(
            displayName="Input River Corridor Mask",
            name="maskCorridor",
            datatype=["DERasterDataset", "DERasterCatalog"],
            parameterType="Required",
            direction="Input")
        
        param6 = arcpy.Parameter(
            displayName="Input DEM",
            name="dem",
            datatype=["DERasterDataset", "DERasterCatalog"],
            parameterType="Required",
            direction="Input")

        param7 = arcpy.Parameter(
            displayName="DEM Scale Value",
            name="scale",
            datatype=["GPDouble"],
            parameterType="Required",
            direction="Input")
        param7.value = 1

        param8 = arcpy.Parameter(
            displayName="Minimum Pixel Size of River Zone",
            name="pixel size",
            datatype=["GPLong"],
            parameterType="Required",
            direction="Input")
        param8.value = 10

        param9 = arcpy.Parameter(
            displayName="Output Migration Raster",
            name="migration",
            datatype=["DERasterDataset", "DERasterCatalog"],
            parameterType="Required",
            direction="Output")

        param10 = arcpy.Parameter(
            displayName="Output Erosion and Deposition Polygons",
            name="volume",
            datatype=["DEFeatureClass"],
            parameterType="Required",
            direction="Output")

        params = [param0,param1,param2,param3,param4,param5,param6,param7,param8,param9,param10]
        return params

    def execute(self, parameters, messages):
        """The source code of the tool."""
        arcpy.CheckOutExtension('Spatial')
        arcpy.env.overwriteOutput = True
        # Input Rasters
        nir_old = arcpy.Raster(parameters[0].valueAsText)
        green_old = arcpy.Raster(parameters[1].valueAsText)
        nir_new = arcpy.Raster(parameters[2].valueAsText)
        green_new = arcpy.Raster(parameters[3].valueAsText)
        mask_classification = arcpy.Raster(parameters[4].valueAsText)
        mask_corridor = arcpy.Raster(parameters[5].valueAsText)
        dem = arcpy.Raster(parameters[6].valueAsText)

        # Input Values
        scale = float(parameters[7].valueAsText)
        min_size = int(parameters[8].valueAsText)

        # Outputs
        output_migration = parameters[9].valueAsText
        output_volumes = parameters[10].valueAsText

        # Compute NDWIs
        ndwi_old = 'ndwi_old.tif'
        ndwi_new = 'ndwi_new.tif'
        ndwi_function(nir_old,green_old, ndwi_old)
        ndwi_function(nir_new,green_new, ndwi_new)

        # Determine Thresholds
        thresh_old = threshold_function(arcpy.Raster(ndwi_old),mask_classification,255,os.path.join(arcpy.env.workspace,'old.csv'))
        thresh_new = threshold_function(arcpy.Raster(ndwi_new),mask_classification,255,os.path.join(arcpy.env.workspace,'new.csv'))

        # Create River Rasters
        river_old = 'river_old.tif'
        river_new = 'river_new.tif'
        river_function(arcpy.Raster(ndwi_old),thresh_old,min_size,'Old Raster',river_old)
        river_function(arcpy.Raster(ndwi_new),thresh_new,min_size,'New Raster',river_new)

        # Migration
        arcpy.env.cellSize = 'MAXOF'
        migration_function(arcpy.Raster(river_old),arcpy.Raster(river_new),mask_corridor,output_migration)

        # Erosion and Deposition Volumes
        arcpy.env.cellSize = 'MINOF'
        migration_raster = arcpy.Raster(output_migration) 
        volume_function(migration_raster,dem,scale,output_volumes)
        arcpy.env.cellSize = 'MAXOF'

        arcpy.CheckInExtension('Spatial')
        return
