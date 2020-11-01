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

## Step 1: Create NDWI Raster
**Input:** Green and Near-Infrared bands of aerial image

**Output:** Normalized Difference Water Index (NDWI) raster

