import arcpy
import numpy

# Local variables:
# Input soil shapefile
soil = "E:\UlsterCounty_1903\SL_files\data.gdb\soil"
# Input landcover raster file
ref_raster = "E:\UlsterCounty_1903\SL_files\data.gdb\Clip2_landcover_orangeulster_newyork_2013_draft0213172"
# Output soil raster
py_soil_PolygonToRaster ="E:\UlsterCounty_1903\SL_files\data.gdb\py_soil_PolygonToRaster2"

# Set Geoprocessing environments
arcpy.env.overwriteOutput = True 
arcpy.env.outputCoordinateSystem = arcpy.Describe(ref_raster).spatialReference
arcpy.env.snapRaster = ref_raster
arcpy.env.extent = ref_raster

# Process: Polygon to Raster
arcpy.PolygonToRaster_conversion(soil, "soilgroup", py_soil_PolygonToRaster, "CELL_CENTER", "NONE", "1")


##########################################################
# Raster calculation
ras = arcpy.Raster(ref_raster)
lowerLeft = arcpy.Point(ras.extent.XMin,ras.extent.YMin)

array_landc = arcpy.RasterToNumPyArray(ref_raster, nodata_to_value=-9999)
array_soil = arcpy.RasterToNumPyArray(py_soil_PolygonToRaster, nodata_to_value=-9999)
(max_rows, max_cols) = array_landc.shape

row_Landc = [-9999,3,8,9,10,11,12,13]
col_SOIL = [-9999,2,3,6]
cn_matrix = [[36,60,-9999,79],
             [30,58,71,78],
             [49,69,79,84],
             [0,0,0,0],
             [89,92,94,95],
             [89,92,94,95],
             [89,92,94,95],
             [35,56,70,77]]
##cn_matrix[row_HRLC.index(1)][col_SOIL.index('A')]

out_array = numpy.array([])

# Loop thru all the cells in array
for m in range(max_rows):
    for n in range(max_cols):
        lc_value = array_landc.item(m,n)
        soil_value = array_soil.item(m,n)
        new_value = cn_matrix[row_Landc.index(lc_value)][col_SOIL.index(soil_value)]
        out_array = numpy.append(out_array,new_value)
out_array = out_array.astype(int)
out_array = out_array.reshape((max_rows,max_cols))

myRaster = arcpy.NumPyArrayToRaster(out_array,lowerLeft,ras.meanCellHeight,ras.meanCellHeight,-9999)
myRaster.save("E:\UlsterCounty_1903\SL_files\data.gdb\py_myRandomRaster")
