# Import arcpy module
import arcpy
from arcpy import env
from arcpy.sa import *

# Local variables:
in_soil = arcpy.GetParameterAsText(0)
in_landcover = arcpy.GetParameterAsText(1)
cn = arcpy.GetParameterAsText(2)
soil = in_soil+"_ras"
# Set Geoprocessing environments
arcpy.env.overwriteOutput = True 
arcpy.env.outputCoordinateSystem = arcpy.Describe(in_landcover).spatialReference
arcpy.env.snapRaster = in_landcover
arcpy.env.extent = in_landcover


soil_class_ori = ["A","B","C","D","A/D","B/D","C/D",None]
soil_class_new = [1,2,3,4,4,4,4,4]

# Process: Add Field
arcpy.AddField_management(in_soil, "soil_class", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

cursor = arcpy.UpdateCursor(in_soil)
row = cursor.next()
while row:
    row.setValue("soil_class", soil_class_new[soil_class_ori.index(row.getValue("hydgrpdcd"))])
    cursor.updateRow(row)
    row = cursor.next()

# Process: Polygon to Raster
arcpy.PolygonToRaster_conversion(in_soil, "soil_class", soil, "CELL_CENTER", "NONE", "1")
soil = Raster(soil)
##soil.save(arcpy.GetParameterAsText(2))
#_________________________________________________________________________
# Process: Reclassify
landcover = Reclassify(in_landcover, "Value","0 90;1 91;2 91;3 92;4 93;5 94;6 95;7 90;8 90;9 90;10 96;11 96;12 96;13 90;14 90;15 90")

# Landcover 3;
cn = Con((landcover == 92)&(soil == 1), 36,)
cn = Con((landcover == 92)&(soil == 2), 60, cn)
cn = Con((landcover == 92)&(soil == 3), 73, cn)
cn = Con((landcover == 92)&(soil == 4), 79, cn)
# Landcover 4;
cn = Con((landcover == 93)&(soil == 1), 35, cn)
cn = Con((landcover == 93)&(soil == 2), 56, cn)
cn = Con((landcover == 93)&(soil == 3), 70, cn)
cn = Con((landcover == 93)&(soil == 4), 77, cn)
# Landcover 5;
cn = Con((landcover == 94)&(soil == 1), 30, cn)
cn = Con((landcover == 94)&(soil == 2), 58, cn)
cn = Con((landcover == 94)&(soil == 3), 71, cn)
cn = Con((landcover == 94)&(soil == 4), 78, cn)
# Landcover 6;
cn = Con((landcover == 95)&(soil == 1), 49, cn)
cn = Con((landcover == 95)&(soil == 2), 69, cn)
cn = Con((landcover == 95)&(soil == 3), 79, cn)
cn = Con((landcover == 95)&(soil == 4), 84, cn)

# Landcover 10,12,13
cn = Con((landcover == 96)&(soil == 1), 62.5, cn)
cn = Con((landcover == 96)&(soil == 2), 76, cn)
cn = Con((landcover == 96)&(soil == 3), 83.5, cn)
cn = Con((landcover == 96)&(soil == 4), 87, cn)

# Out number 0
cn = Con(landcover==91 ,0, cn)

# Landcover 0,7,8,9,13,14,15;
cn = Con((landcover == 90)&(soil == 1), 89, cn)
cn = Con((landcover == 90)&(soil == 2), 92, cn)
cn = Con((landcover == 90)&(soil == 3), 94, cn)
cn = Con((landcover == 90)&(soil == 4), 95, cn)

cn.save(arcpy.GetParameterAsText(2))

