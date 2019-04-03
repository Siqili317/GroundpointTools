import arcpy
import numpy

##Need to specify input soil shapefile (with field named "hydgrpdcd"), landcover raster layer and output file (at the end of code).

# Local variables:
# Input soil shapefile
#soil = "D:\UlsterCounty_1903\SL_files\data.gdb\soil"
soil = arcpy.GetParameterAsText(0)
# Input landcover raster file
ref_raster = "D:\UlsterCounty_1903\SL_files\data.gdb\Clip2_landcover_orangeulster_newyork_2013_draft0213172"
ref_raster = arcpy.GetParameterAsText(1)
# Output soil raster
py_soil_PolygonToRaster ="D:\UlsterCounty_1903\SL_files\data.gdb\pyout_soil2Raster"

# Set Geoprocessing environments
arcpy.env.overwriteOutput = True 
arcpy.env.outputCoordinateSystem = arcpy.Describe(ref_raster).spatialReference
arcpy.env.snapRaster = ref_raster
arcpy.env.extent = ref_raster

soil_class_ori = ["A","B","C","D","A/D","B/D","C/D",None]
soil_class_new = [1,2,3,4,4,4,4,4]

# Process: Add Field
arcpy.AddField_management(soil, "soil_class", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

cursor = arcpy.UpdateCursor(soil)
row = cursor.next()
while row:
    row.setValue("soil_class", soil_class_new[soil_class_ori.index(row.getValue("hydgrpdcd"))])
    cursor.updateRow(row)
    row = cursor.next()

# Process: Polygon to Raster
arcpy.PolygonToRaster_conversion(soil, "soil_class", py_soil_PolygonToRaster, "CELL_CENTER", "NONE", "1")


#_________________________________________________________________________
# Raster calculation
ras = arcpy.Raster(ref_raster)
lowerLeft = arcpy.Point(ras.extent.XMin,ras.extent.YMin)

array_landc = arcpy.RasterToNumPyArray(ref_raster, nodata_to_value=-9999)
array_soil = arcpy.RasterToNumPyArray(py_soil_PolygonToRaster, nodata_to_value=-9999)
(max_rows, max_cols) = array_landc.shape

col_SOIL = [1,2,3,4]
row_Landc = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]

cn_matrix = [[89,92,94,95],
             [0,0,0,0],
             [0,0,0,0],
             [36,60,73,79],
             [35,56,70,77],
             [30,58,71,78],
             [49,69,79,84],
             [89,92,94,95],
             [89,92,94,95],
             [89,92,94,95],
             [62.5,76,83.5,87],
             [62.5,76,83.5,87],
             [62.5,76,83.5,87],
             [89,92,94,95],
             [89,92,94,95],
             [89,92,94,95]]

out_array = numpy.array([])

# Loop thru all the cells in array
for m in range(max_rows):
    for n in range(max_cols):
        lc_value = array_landc.item(m,n)
        soil_value = array_soil.item(m,n)
        if lc_value == -9999:
            new_value  = -9999
        else:
            new_value = cn_matrix[row_Landc.index(lc_value)][col_SOIL.index(soil_value)]

        out_array = numpy.append(out_array,new_value)

out_array = out_array.astype(float)
out_array = out_array.reshape((max_rows,max_cols))

myRaster = arcpy.NumPyArrayToRaster(out_array,lowerLeft,ras.meanCellHeight,ras.meanCellHeight,-9999)
myRaster.save(arcpy.GetParameterAsText(2))

