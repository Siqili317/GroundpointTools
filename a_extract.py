import csv, os, re, numpy, arcpy

# ws_name = 'ALB';
arcpy.env.workspace = arcpy.GetParameterAsText(1)
arcpy.env.overwriteOutput = True

ws_name =  arcpy.GetParameterAsText(2)

output=arcpy.GetParameterAsText(1) +'/'+ ws_name+"_field_data.csv"
not_extracted=arcpy.GetParameterAsText(1) +'/'+ ws_name+"_not_extracted.csv"

arcpy.AddMessage(output)
arcpy.AddMessage(not_extracted)

f_out = open(output, 'wb') #output file for extracted culverts
not_extracted_out= open(not_extracted, 'wb') #output for crossings not extracted
writer = csv.writer(f_out) #write object
writer_no_extract=csv.writer(not_extracted_out)

#write headings
writer.writerow(['BarrierID','NAACC_ID','Lat','Long','Rd_Name','Culv_Mat','In_Type','In_Shape','In_A','In_B','HW','Slope','Length','Flags']) #header row
writer_no_extract.writerow(['Survey_ID','NAACC_ID','Lat','Long','Rd_Name','Culv_Mat','In_Type','In_Shape','In_A','In_B','HW','Slope','Length','Flags']) #header row

raw_data = arcpy.GetParameterAsText(0)
# raw_data = "NY_Ulster_excel_detailed.csv"
with open (raw_data) as f:
	input_table = csv.reader(f)
	input_table_array = []

	# Find the title row ID. The row starts with 'Survey_Id'
	first_col = []
	for row in input_table:
		input_table_array.append(row)
		first_col.append(row[0])
	title_ID = first_col.index('Survey_Id')

# Remove rows above title row
for i in range(title_ID):
	del input_table_array[0]
title_row = input_table_array[0]

# eliminate blank cells from data and add data to array
for row in input_table_array[1:]:
	for i in range(len(title_row)):
		if len(row[i]) ==0:
			row[i] =-1 #Value from Cornel extract.py 


k = 1; 
for row in input_table_array[1:]:
	BarrierID = str(k)+ws_name
	Survey_ID = row[title_row.index('Survey_Id')]
	NAACC_ID = row[title_row.index('Naacc_Culvert_Id')]


	Lat = float(row[title_row.index('GPS_Y_Coordinate')])
	Long = float(row[title_row.index('GPS_X_Coordinate')])
	Road_Name = row[title_row.index('Road')]
	Culv_material = row[title_row.index('Material')]
	
	# Assign inlet type and then convert to language accepted by capacity_prep script
	Inlet_type_ID = title_row.index('Inlet_Type')
	Inlet_type=row[Inlet_type_ID]
	# print Inlet_type
	if Inlet_type=="Headwall and Wingwalls":
		Inlet_type="Wingwall and Headwall"
	elif Inlet_type=="Wingwalls":
		Inlet_type='Wingwall'
	elif Inlet_type=='None':
		Inlet_type='Projecting'
	# print Inlet_type

	# Assign culvert shape and then convert to language accepted by capacity_prep script

	Inlet_Shape=row[title_row.index('Inlet_Structure_Type')]
	# print Inlet_Shape
	if Inlet_Shape=='Round Culvert':
		Inlet_Shape='Round'
	elif Inlet_Shape=='Pipe Arch/Elliptical Culvert':
		Inlet_Shape="Elliptical"
	elif Inlet_Shape=='Box Culvert':
		Inlet_Shape='Box'
	elif Inlet_Shape=='Box/Bridge with Abutments':
		Inlet_Shape='Box'
	elif Inlet_Shape=='Open Bottom Arch Bridge/Culvert':
		Inlet_Shape='Arch'

	Inlet_A=float(row[title_row.index('Inlet_Width')]) # Inlet_A = Inlet_Width
	Inlet_B=float(row[title_row.index('Inlet_Height')]) # Inlet B = Inlet Height
	HW=float(row[title_row.index('Road_Fill_Height')]) #This is from the top of the culvert, make sure the next step adds the culvert height
	Slope=float(row[title_row.index('Slope_Percent')]) 
	if Slope<0: # Negatives slopes are assumed to be zero
	    Slope=0
	Length=float(row[title_row.index('Crossing_Structure_Length')])
	# Outlet_shape=CD[55]
	# Outlet_A=float(CD[58])
	# Outlet_B=float(CD[54])
	# Comments=CD[8]
	Number_of_culverts=float(row[title_row.index('Number_Of_Culverts')])
	# print(Number_of_culverts)
	if Number_of_culverts > 1:
		if Number_of_culverts == 2:
		    Flags=2 # the crossing has two culverts
		elif Number_of_culverts == 3:
		    Flags=3 # The crossing has three culverts
		elif Number_of_culverts == 4:
		    Flags=4 # The crossing has four culverts
		elif Number_of_culverts == 5:
		    Flags=5 # The crossings has five culverts
		elif Number_of_culverts == 6:
		    Flags=6 # The crossing has six culverts
		elif Number_of_culverts == 7:
		    Flags=7 # The crossings has seven culverts
		elif Number_of_culverts == 8:
		    Flags=8 # The crossings has eight culverts
		elif Number_of_culverts == 9:
		    Flags=9 # The crossings has nine culverts
		elif Number_of_culverts == 10:
		    Flags=10 # The crossings has ten culverts                              
	else:
	    Flags=0


	Neg_test=[Inlet_A,Inlet_B,HW,Length] # This step eliminates rows with negative values of Inlet_A, Inlet_B, HW, or Length from the analysis
	N=0
	for i in range(0,4):
		if Neg_test[i]<0:
			N=N+1
            
	if row[title_row.index('Crossing_Type')]!="Bridge" and N==0:
        # Bridge crossings are not modeled
        # From Allison, 8/16/17: There are other types of crossings we do not model that are missed by this (e.g., ford, buried stream)
		writer.writerow([BarrierID, NAACC_ID, Lat, Long, Road_Name, Culv_material, Inlet_type, Inlet_Shape, Inlet_A, Inlet_B, HW, Slope,Length, Flags])
		k=k+1
	elif row[title_row.index('Inlet_Structure_Type')]=="Box/Bridge with Abutments" and Inlet_A<20 and N==0:
        # Bridge crossings less than 20 ft are considered culverts (question from Allison, 8/16/17: why do we not model Crossing_Type == Bridge AND Outlet_Type == Box Culvert?)
		writer.writerow([BarrierID, NAACC_ID, Lat, Long, Road_Name, Culv_material, Inlet_type, Inlet_Shape, Inlet_A, Inlet_B, HW, Slope,Length, Flags])
		k=k+1
	elif row[title_row.index('Inlet_Structure_Type')]=="Open Bottom Arch Bridge/Culvert" and Inlet_A<20 and N==0:
        # Bridge crossings less than 20 ft are considered culverts (see above question from Allison)
		writer.writerow([BarrierID, NAACC_ID, Lat, Long, Road_Name, Culv_material, Inlet_type, Inlet_Shape, Inlet_A, Inlet_B, HW, Slope,Length, Flags])
		k=k+1
	else:
		writer_no_extract.writerow([Survey_ID, NAACC_ID, Lat, Long, Road_Name, Culv_material, Inlet_type, Inlet_Shape, Inlet_A, Inlet_B, HW, Slope,Length, Flags])

f.close()
f_out.close()
not_extracted_out.close()