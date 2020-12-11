# AIMM
The Aerial Imagery Migration Model (AIMM) is a tool for estimating the volume of sediment lost to lateral riverbank erosion. This ArcGIS Pro tool requires two RGBI images of a river corridor and a high-resolution DEM as inputs and outputs a map of river migration as well as polygons of erosion and deposition with associated volumes. You can read the paper describing the model in further detail [here](https://doi.org/10.1016/j.geomorph.2020.107313). Before using the tool, **I strongly recommend working through the tutorial with the provided example data.** This will familiarize you with the components of the tool, and very likely make your own analysis proceed much more smoothly.

# Contents
- [Installation](#installation)
- [Tutorial](#tutorial)
    - [Step 1](#step-1-create-ndwi-rasters)
    - [Step 2](#step-2-compute-thresholds)
    - [Step 3](#step-3-create-river-rasters)
    - [Step 4](#step-4-create-migration-raster)
    - [Step 5](#step-5-calculate-volumes)
    - [Full Model](#full-model-AIMM)
- [Contact](#contact)
- [Citation](#citation)

# Installation
## Requirements
AIMM requires an ArcGIS Pro conda environment with scikit-image installed. [Learn more about ArcGIS Pro Conda Environments](https://pro.arcgis.com/en/pro-app/arcpy/get-started/what-is-conda.htm).

## Download Files
You can download the model files by clicking on the Code button above and then selecting Download ZIP. Download the files, then unzip them in your chosen location.

## Open the Toolbox
Detailed instructions for opening ArcPro toolboxes can be found [here](https://pro.arcgis.com/en/pro-app/help/projects/connect-to-a-toolbox.htm). In short however, within ArcGIS Pro you will need to add a folder connection to the *toolbox* folder of the *AIMM_Stable* directory. Once added you should be able to click on the AIMM toolbox and open your desired tool.

# Tutorial
## Tools
The AIMM toolbox contains six tools:
1. Create NDWI Raster
2. Compute Threshold
3. Create River Raster
4. Create Migration Raster
5. Calculate Volumes
6. AIMM

The first five tools will run the individual components of the AIMM model, while the sixth tool (AIMM) will run the full model. This tutorial walks through each of the five components then describes the use of the full model tool.

## Step 0: Data Preparation
This tutorial will use the example data found in the *AIMM_Stable\example_data* folder, but a user's own data can be used as well. The example data includes two aerial images of the East Nishnabotna river near Oakland, Iowa from 2009 and 2018, a LiDAR-derived DEM that covers the same area, and a mask derived from a one river-width buffer of the river's centerline.

## Step 1: Create NDWI Rasters
**Input:** Green and Near-Infrared bands of aerial image as rasters

**Output:** Normalized Difference Water Index (NDWI) raster

The NDWI index highlights the occurence of water in the landscape and is calucated according to the formula:

    NDWI = green - infrared / green + infrared

The green and infrared bands are inputed as seperate rasters. To export image bands as seperate rasters:
1. Click on the dropdown icon to show the raster's bands
2. Right click on your desired band and click *Export to Different Format*
3. Save the raster in your desired location

For the first year's data (2009) the tool inputs should look like this:
![Tool Screen NDWI Raster](https://github.com/forrestfwilliams/AIMM_Stable/blob/master/assets/images/create_ndwi.JPG)

And the output NDWI Raster should look like this:
![Output NDWI Raster](https://github.com/forrestfwilliams/AIMM_Stable/blob/master/assets/images/out_ndwi.JPG)

Repeat the use of this tool for the second year's data (2018).

## Step 2: Compute Thresholds
**Input:** NDWI raster, River classification mask

**Output:** Threshold for river classification (.txt)

To determine where the river occurs within the NDWI image, AIMM uses the [Li Threshold Method](https://scikit-image.org/docs/dev/auto_examples/developers/plot_threshold_li.html) to segment the image into areas of high and low NDWI values. Areas of high NDWI represent water, and areas of low NDWI represent land.

In order to get a more balanced sample, this tool only uses raster cells within a mask to perform the thresholding. Cells with the value 0 will be included in the analysis, and cells with a NoData value will be excluded. The user is free to use any mask they choose, but in general a one-width buffer of the river is appropriate.

The tool prints the threshold value to the console and also saves the value in a user-specified .txt file.

For the first year's data (2009) the tool inputs and output should look like this:
![Tool Screen Thresholds](https://github.com/forrestfwilliams/AIMM_Stable/blob/master/assets/images/compute_threshold.JPG)
You will notice that the thresholds are printed to the ArcGIS Pro console, as well as saved in the specified file.

Repeat the use of this tool for the second year's data (2018).

## Step 3: Create River Rasters
**Input:** NDWI raster, Threshold value, Minimum size of river zone

**Output:** River raster

Using the threshold value identified in the previous step, this step reclassifies the NDWI image to identify the river in the image and perform some cleaning operations. Either copy the threshold value from the console, or retrieve it from the text file that **Step 2** created. **Make sure you use the correct threshold for each image, they will be different!**

Also, you need to tell the tool if you are creating the Old or New river raster, since the raster value that corresponds with the river is different for each year. In the old year's river raster, a value of 0 is land and 1 is river, but in the new year's river raster 0 is land and 2 is river.

For the first year's data (2009) the tool inputs and output should look like this:
![Tool Screen River Raster](https://github.com/forrestfwilliams/AIMM_Stable/blob/master/assets/images/create_river.JPG)

And the output River raster should look like this:
![Output River Raster](https://github.com/forrestfwilliams/AIMM_Stable/blob/master/assets/images/out_river.JPG)

Repeat the use of this tool for the second year's data (2018).

## Step 4: Create Migration Raster
**Inputs:** Old and New river rasters, River corridor mask

**Outputs:** Migration Raster

Using the Old and New River raster created in the previous step, this step overlays these two rasters and outputs a migration raster that contains integer values that correspond to zones of stable land, stable river, erosion and deposition. A cell that was river in the Old raster but land in the New raster is classified as deposition, and a cell that was land in the Old raster but river in the New raster is classified as erosion. The values for each category are:

|Raster Value   |Category       |
|:--------------|--------------:|
|      0        |Stable Land    |
|      1        |Deposition     |
|      2        |Erosion        |
|      3        |Stable Channel |

Additionally, the River corridor mask is used to restrict the analysis to the active channel and all raster cells that fall outside of this mask are classified as stable land (0). Once again cells with the value 0 will be included in the analysis, and cells with a NoData value will be excluded. A one-width buffer mask can still be appropriate for this mask, but a mask that includes a larger portion of the river corridor may be needed.

If planform migration is the desired output from AIMM, you can stop processing here and use the Migration raster as your final output. If you want to calculate volumes of erosion and deposition, continue to Step 5.

The tool inputs and output for Step 4 should look like this:
![Tool Screen Migration](https://github.com/forrestfwilliams/AIMM_Stable/blob/master/assets/images/migration.JPG)

And the output Migration raster should look like this:
![Output Migration](https://github.com/forrestfwilliams/AIMM_Stable/blob/master/assets/images/migration.JPG)

## Step 5: Calculate Volumes
**Inputs:** Migration raster, DEM, DEM scale value

**Outputs:** Erosion and Deposition polygons

The final step of AIMM uses the migration raster and DEM as input and ouputs polygons of erosion and deposition with their associated area and volume as fields in their attribute table. The height of each zone of erosion/deposition is estimate separately and the heights of erosion and deposition polygons are estimated using different methods.

For erosion polygons, the heights are estimated by multiplying the standard deviation of the DEM cells within the erosion polygon by four. This value roughly approximates the range of the elevaiton values, but limits the influence of outlier values. For deposition polygons, the heights are estimated by subtracting the minimum DEM value from the median DEM value within the deposition polygon.

The tool will calculate areas in units of m<sup>2</sup> and volumes in units of m<sup>3</sup>. The areas are automatically calculated in units of m<sup>2</sup> by ArcGIS Pro using raster projection information, but setting the DEM scale value is sometimes nessecary to convert DEM values to meters. The DEM scale value multiplies DEM by a constant value according to the formula:

    Output DEM = Input DEM * DEM Scale Value

For example, if your DEM is in units of centimeters, setting the DEM scale value to 0.01 will give you the correct output.

The tool inputs and output for Step 5 should look like this:
![Tool Screen Volume](https://github.com/forrestfwilliams/AIMM_Stable/blob/master/assets/images/calculate_volume.JPG)

And the output erosion and deposition polygons should look likes this:
![Output Volume](https://github.com/forrestfwilliams/AIMM_Stable/blob/master/assets/images/out_volume.JPG)

## Full Model: AIMM
**Inputs:**
- Old and New infrared rasters [(Step 1)](#step-1-create-ndwi-rasters)
- Old and New green rasters [(Step 1)](#step-1-create-ndwi-rasters)
- River classification mask [(Step 2)](#step-2-compute-thresholds)
- Minimum size of river zone [(Step 3)](#step-3-create-river-rasters)
- River corridor mask [(Step 4)](#step-4-create-migration-raster)
- DEM scale value [(Step 5)](#step-5-calculate-volumes)

**Outputs:**
- Migration Raster [(Step 4)](#step-4-create-migration-raster)
- Erosion and Deposition Polygons [(Step 5)](#step-5-calculate-volumes)

Running the model one step at a time will you provide with a better understanding of the model and also allow you to check your results at each step, but the AIMM tool will you allow to run the AIMM model in one step. Detailed information on each model input and output can found in its respective section. An important caveat of this tool is that intermediate data such as River rasters and River threshold values and are not an output of this tool. River raster can however be derived from the output Migration by using the following reclassificaitons:

**Old River Raster**
|Old Value  |New Value  |
|:----------|----------:|
|0          |0          |
|1          |1          |
|2          |0          |
|3          |1          |

**New River Raster**
|Old Value  |New Value  |
|:----------|----------:|
|0          |0          |
|1          |0          |
|2          |2          |
|3          |2          |

Currently, the model must be run in stepwise if you desire to know the threshold values used in the classification. This however can be changed if others desire this functionality.

# Contact
If you encounter issues with AIMM, please create an issue within this repository. Questions related to the AIMM can also be emailed to Forrest Williams at F.WILLIAMS1@massey.ac.nz. This tool is used within ongoing research conducted at Iowa State's [Applied Geomorphology Lab](https://www.nrem.iastate.edu/research/moore/).

# Citation
Williams, Forrest, et al. "Automated measurement of eroding streambank volume from high-resolution aerial imagery and terrain analysis." Geomorphology 367 (2020): 107313.
