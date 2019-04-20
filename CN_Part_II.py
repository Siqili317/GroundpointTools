# Import arcpy module

import arcpy
from arcpy import env
from arcpy.sa import *

# Set Geoprocessing environments
arcpy.env.workspace = arcpy.GetParameterAsText(0)
# Local variables:
in_dem = arcpy.GetParameterAsText(3)
in_cn = arcpy.GetParameterAsText(4)
in_culvert = arcpy.GetParameterAsText(5)
arcpy.AddMessage(type(in_culvert))
surveyID = arcpy.GetParameterAsText(6)
if not surveyID:
        surveyID == "ObjectID"
in_flowdir = arcpy.GetParameterAsText(7)
in_slope = arcpy.GetParameterAsText(8)
in_watershed =  arcpy.GetParameterAsText(9)
prjname = arcpy.GetParameterAsText(1) + "_" + arcpy.GetParameterAsText(2)
out_cn = prjname + "_CNclip"
out_flowdir = prjname + "_FlowDir"
out_watershed = prjname + "_Watershed"
# Set Geoprocessing environments
arcpy.env.overwriteOutput = True 
arcpy.env.outputCoordinateSystem = arcpy.Describe(in_dem).spatialReference
arcpy.env.snapRaster = in_dem
arcpy.env.extent = in_dem

#CN RESAMPLE
#______________________________________________________________________________
if not isinstance(in_cn,Raster):
        in_cn = Raster(in_cn)

# Resample input CN to have the same spatial reference, extent and cell size with input DEM
cellsizex = arcpy.GetRasterProperties_management(in_dem, "CELLSIZEX")
cellsizex = str(cellsizex.getOutput(0))
cellsizey = arcpy.GetRasterProperties_management(in_dem, "CELLSIZEY")
cellsizey = str(cellsizey.getOutput(0))
arcpy.AddMessage(cellsizey)
cellsize = cellsizex + " " + cellsizey
arcpy.Resample_management(in_cn, out_cn, cellsize, "BILINEAR")

#DATA_PREPARETION
#______________________________________________________________________________
# Check and prepare flow direction/slope/watershed polygon inputs.
if not isinstance(in_flowdir,Raster):
        # Process: Flow Direction
        arcpy.gp.FlowDirection_sa(in_dem, out_flowdir, "NORMAL")
        in_flowdir = out_flowdir

if not isinstance(in_slope,Raster):
        # Process: Slope
        out_slope = Slope(in_dem)
        out_slope.save(prjname+"_Slope")
        in_slope = out_slope
        
if not in_watershed:
        # Process: Watershed
        out_WatershedRaster = Watershed(in_flowdir, in_culvert, surveyID)
        arcpy.RasterToPolygon_conversion(out_WatershedRaster, "in_memory/pols", "SIMPLIFY", "VALUE")
        arcpy.Dissolve_management("in_memory/pols",out_watershed,"gridcode")
        in_watershed = out_watershed

#ZONAL STATISTICS
#______________________________________________________________________________

