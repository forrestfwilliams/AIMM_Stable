# AIMM
The Aerial Imagery Migration Model (AIMM) is tool for estimating the volume of sediment lost to lateral riverbank erosion. The tool requires two RGBI images of a river corridor and a high-resolution DEM as inputs and outputs a map of river migration as well as polygons of erosion and deposition with associated volumes. You can read the paper describing the model in further detail [here](https://doi.org/10.1016/j.geomorph.2020.107313).

# Installation
## Requirements
AIMM requires an ArcGIS Pro conda environment with scikit-image installed. [Learn more about ArcGIS Pro Conda Environments](https://pro.arcgis.com/en/pro-app/arcpy/get-started/what-is-conda.htm)

## Download Files
You can download the model files by clicking on the Code button above and then selecting Download ZIP. Download the files, then unzip them in your chosen location

## Open the Toolbox
Detailed instructions for open toolboxes can be found [here](https://pro.arcgis.com/en/pro-app/help/projects/connect-to-a-toolbox.htm). In short however, within ArcGIS Pro you will need to add a folder connection to the *toolbox* folder of the *AIMM_Stable*. Once added you should be able to click on the AIMM toolbox and open your desired tool.

# Tutorial
## Tools
The AIMM toolbox contains six tools:
1. Create NDWI Raster
2. Compute Threshold
3. Create River Raster
4. Create Migration Raster
5. Calculate Volumes
6. AIMM

The first five tools will run the individual components of the AIMM model, while the sixth tool (AIMM) will run the full model. This tutorial walks through each of the five components then describes the use of the full model.

## Step 0: Data Preparation
This tutorial will use the example data found in the *AIMM_Stable\example_data* folder, but a user's own data can be used as well.

## Step 1: Create NDWI Rasters
**Input:** Green and Near-Infrared bands of aerial image as rasters

**Output:** Normalized Difference Water Index (NDWI) raster

The NDWI index highlights the occurence of water in the landscape and is calucated according to the formula:

    NDWI = green - infrared / green + infrared

The green and infrared bands are inputed as seperate rasters. To export images bands as seperate rasters:
1. Click on the dropdown icon to show the raster's bands
2. Right click on your desired band and click *Export to Different Format*
3. Save the raster in your desired location

For the first year's data (2009) the tool inputs should look like this:
![Create NDWI Raster](/assets/images/create_ndwi.jpg)

And the output NDWI Raster should look like this:
![Output NDWI Raster](/assets/images/out_ndwi.jpg)

Repeat the use of this tool for the second year's data (2018).

## Step 2: Compute Threshold
**Input:** NDWI raster, classification mask

**Output:** Threshold for river classification (.txt)

To determine where the river occurs within the NDWI image, AIMM uses the [Li Threshold Method](https://scikit-image.org/docs/dev/auto_examples/developers/plot_threshold_li.html) to segment the image into areas of high and low NDWI values. Areas of high NDWI represent water, and areas of low NDWI represent land.

In order to get a more balanced sample, this tool only uses raster cells within a mask to perform the thresholding. Cells with the value 0 will be included in the analysis, and cell with a NoData value will be excluded. The user is free to use any mask they choose, but in general a one-width buffer of the river is appropriate.

The tool prints the threshold value to the console and also saves the value in a user-specified .txt file.

For the first year's data (2009) the tool inputs and output should look like this:
![Output NDWI Raster](/assets/images/compute_threshold.jpg)

Repeat the use of this tool for the second year's data (2018).