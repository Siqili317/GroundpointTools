# Import arcpy module

import arcpy
from arcpy import env
from arcpy.sa import *

# Set Geoprocessing environments
arcpy.env.workspace = arcpy.GetParameterAsText(0)
# Local variables:
in_dem = arcpy.GetParameterAsText(0)
in_cn = arcpy.GetParameterAsText(1)

out_cn = arcpy.GetParameterAsText(2)

# Set Geoprocessing environments
arcpy.env.overwriteOutput = True 
arcpy.env.outputCoordinateSystem = arcpy.Describe(in_dem).spatialReference
arcpy.env.snapRaster = in_dem
arcpy.env.extent = in_dem

#CN RESAMPLE
#______________________________________________________________________________

cellsizex = arcpy.GetRasterProperties_management(in_dem, "CELLSIZEX")
cellsizex = str(cellsizex.getOutput(0))
cellsizey = arcpy.GetRasterProperties_management(in_dem, "CELLSIZEY")
cellsizey = str(cellsizey.getOutput(0))
arcpy.AddMessage(cellsizey)
cellsize = cellsizex + " " + cellsizey
arcpy.Resample_management(in_cn, out_cn, cellsize, "BILINEAR")



