#! /usr/bin/env python3

from PIL import Image, ImageDraw, ImageFont, ImageOps
import matplotlib.pyplot as mpl
import math
import numpy as np
from skimage.draw import (line, 
                          disk,
                          rectangle)


# Colors ----------------------------
white       = ( 1.0, 1.0, 1.0 )
black       = ( 0.0, 0.0, 0.0 )
wheel_color = ( 0.0, 0.1, 0.5 )


#---------------------------------------
# Return colors to represent regolith
# density. Gray value gets darker as 
# depth increases.
#---------------------------------------
def gray_value_for_depth ( depth ) :
  if depth <= 6 :
    return 0.9 - 0.1 * depth
  elif depth <= 11 :
    return 0.25 - 0.05 * (depth - 7)
  else :
    return 0.0



#----------------------------------------------------------
# I got these constants by running this program and 
# printing out the density values from 0 to 29 cm deep.
#----------------------------------------------------------
min_density = 1.101
max_density = 1.818
density_range = max_density - min_density


#-----------------------------------------------------
# There are two vehicles here. Uncomment whichever
# one you want to simulate. The wheel contact areas 
# are an estimate based on wheel width. 
# The PP&L bulldozer is fictional (so far). It has a 
# larger contact area than the Apollo rover because
# it is a large, heavy construction vehicle.
#-----------------------------------------------------


# Choose one of these, and comment out the other one.
#scenario = "Moon_Buggy"
scenario = "PP&L"




if scenario == "Moon_Buggy" :
  # Apollo Lunar rover  ------------------------------------------
  vehicle_name       = "Apollo Rover"
  mass_of_vehicle    = 660  # kg
  wheel_width        = 15   # cm (will be squared)
  n_wheels           = 4
elif scenario == "PP&L" :
  # Peary Power and Light bulldozer ------------------------------
  vehicle_name       = "PP&L Bulldozer"
  mass_of_vehicle    = 6000  # kg
  wheel_width        = 10    # cm (will be squared)
  n_wheels           = 4
else :
  print ( "Bad scenario!" )
  sys.exit ( 1 )



lunar_gravity          = 1.6   # meters / second
force_to_support       = mass_of_vehicle * lunar_gravity  # Newtons
force_per_wheel        = force_to_support / n_wheels

# Shallow angle of force-spreading with depth, because 
# we do not see little depressed areas around the Apollo
# astronauts' footprints.
angle_of_force_spread  = 5     # degrees
force_spread           = math.tan(math.radians(angle_of_force_spread))


# This is the density to which each overloaded 
# layer will collapse.
grain_density = 2.0    # g/cm3

#----------------------------------------------------------
# These constants are from NASA page:
# https://ntrs.nasa.gov/citations/19720035207
# The min value at near-surface and the max value at
# 30 cm is all they gave me. No formula.
# So I will scale it linearly with depth, which could
# probably be improved.
#----------------------------------------------------------
min_bearing_cap   = 0.03   # Newtons per square cm
bearing_per_cm    = 65.0 / 30


def density_and_bearing_cap_at_depth ( depth ) :
  density  = 1.89 * (depth + 1.69) / (depth + 2.9)
  bearing_cap = min_bearing_cap + depth * bearing_per_cm
  return density, bearing_cap


#============================================
# Main 
#============================================

#-------------------------------------------------
# Pre-calculate density and bearing capacity for
# each centimeter down to 30, and store the values
# in arrays.
#-------------------------------------------------
max_depth = 30
density     = []
bearing_cap = []

for depth in range(max_depth) :
  d, c = density_and_bearing_cap_at_depth ( depth )
  print ( f"depth {depth} cap {c}" )
  density.append(d)
  bearing_cap.append(c)


# Array to store each compressed layer's width,
# compressed height, and force per cm2
compressed_layers = []


#--------------------------------------------------
# Compress the layers!
# Check each layer to see if it can support the 
# load on it. If the force per cm2 is too great,
# then the layer collapses to its grain density,
# and all force is transferred down to the next 
# deeper layer.
# But the force footprint grows a little every
# time, because of some interlocking between 
# particles offf to the side. The angle of growth
# is apparently not very great with lunar regolith
# or you would be able to see little depressed areas
# around the Apollo footprints.
# When you reach a point where the soil's load
# bearing capacity is greater than or equal to 
# the load per cm2, compression stops.
#--------------------------------------------------
total_compression        = 0.0
first_uncompressed_layer = 0
max_pressure             = 0
min_pressure             = 10000
support_footprint_edge   = wheel_width

for depth in range(max_depth) :
  downward_force = force_per_wheel / support_footprint_edge ** 2
  print ( f"depth {depth} downward_force == {downward_force}" )

  # Store the max and min pressure,
  # for later display purposes.
  if downward_force > max_pressure :
    max_pressure = downward_force
  if downward_force < min_pressure :
    min_pressure = downward_force

  support = bearing_cap [ depth ]
  print ( f"  support {support}" )

  # Is the support at this level greater than
  # or equal to the load per square cm?
  if support >= downward_force :
    # Yes! This layer does not compress, 
    # so its thickness remains at 1.0 cm.
    first_uncompressed_layer = depth
    #compressed_layers.append( (support_footprint_edge, 1.0, downward_force) )
    print ( "  load is supported." )
    break
  
  # This layer cannot support the load, 
  # so it collapses to grain density.
  pre_collapse_density = density [ depth ]
  new_layer_thickness = pre_collapse_density / grain_density
  total_compression += (1.0 - new_layer_thickness)
  print ( f"  new_layer_thickness == {new_layer_thickness}" )
  print ( f"  total_compression   == {total_compression}" )

  compressed_layers.append( (support_footprint_edge, new_layer_thickness, downward_force) )

  # The footprint increases at a shallow angle as
  # it goes down. So for each new cm of depth, the 
  # previous support-square edge length increases by 
  # twice the spread amount, which was calculated
  # above.
  support_footprint_edge += 2 * force_spread




#=====================================================
# render the compression image
#=====================================================
# Make the image.
image_height = 1000
image_width  = 2000
img = np.full((image_height, image_width, 3), 200, dtype=np.double)
pixels_per_cm = 50

# Draw a line for each cm of depth, starting at ground level
ground_level = 200

mpl.rcParams.update({'font.size': 5})
y = ground_level
first_uncompressed_layer_y = 0


#-----------------------------------------------------------
# Draw all the original layers of regolith,
# with darker gray values representing increasing density.
#-----------------------------------------------------------
for i in range(12) :
  layer_density = density[i]
  layer_bc      = bearing_cap[i]
  percent_density = layer_density / grain_density
  percent_density *= 0.75  # I just want the gray values to be lighter.
  print ( f"density {layer_density} {percent_density}" )
  gray = gray_value_for_depth(i)
  print ( f"gray: {gray}" )
  # Draw rect -------
  rect_start  = (y, 0)
  rect_height = pixels_per_cm
  rect_width  = image_width
  rect_extent = (rect_height, rect_width)
  rr, cc = rectangle(rect_start, extent=rect_extent, shape=img.shape)
  img[rr, cc] = (gray, gray, gray)
  if i == first_uncompressed_layer :
    first_uncompressed_layer_y = y
  # Label this rect ------------
  left_label  = f"depth {i+1}: {layer_density:.2f} g/cm3"
  right_label = f"bearing cap: {layer_bc:.2f} N/cm2"
  g = white
  if i < 4 :
    g = black
  mpl.text ( 300,  y + 30, left_label,  color=g )
  mpl.text ( 1400, y + 30, right_label, color=g )
  # Draw line -----
  rr, cc = line ( y, 0, y, image_width-1)
  img[rr, cc] = black
  # Advance the y value one cm lower
  y += pixels_per_cm


#------------------------------------------------
# Draw the compressed layers, in red.
# The topmost layer starts at the total
# compression amount, and we work downward 
# from there.
#------------------------------------------------
pressure_range = max_pressure - min_pressure
y = first_uncompressed_layer_y - pixels_per_cm
n_compressed_layers = len(compressed_layers)
image_x_center = image_width / 2
first_layer_width = 0
first_layer_left_edge = 0
y = ground_level + total_compression * pixels_per_cm

for i in range(n_compressed_layers) :
  print ( f" i == {i}" )
  layer = compressed_layers[i]
  layer_width  = layer[0] * pixels_per_cm
  layer_height = layer[1] * pixels_per_cm
  print ( f"draw compressed layer {i} height {layer_height}" )
  # Draw rect -------
  layer_left_edge = image_x_center - layer_width / 2
  if i == 0 :
    first_layer_left_edge = layer_left_edge
    first_layer_width = layer_width
  rect_start  = (y, layer_left_edge)
  rect_extent = (layer_height, layer_width)
  rr, cc = rectangle(rect_start, extent=rect_extent, shape=img.shape)

  # The brightest red will be the highest pressure
  pressure_here = layer[2]
  label = f"{pressure_here:.2f} N/cm2"
  mpl.text ( image_x_center - 100,  y + 30, label,  color=g )
  pressure_percent = (pressure_here - min_pressure) / pressure_range
  img[rr, cc] = (pressure_percent, 0.0, 0.0)

  y += layer_height

# Draw a white line at the top of the first 
# uncompressed layer, so it's easier to see.
line_y = first_uncompressed_layer_y
rr, cc = line ( line_y, 0, line_y, image_width-1)
img[rr, cc] = white

# Draw the wheel that is causing all 
# this compression.
wheel_bottom = ground_level + total_compression * pixels_per_cm
rect_start  = (0, first_layer_left_edge)
rect_extent = (wheel_bottom, first_layer_width)
rr, cc = rectangle(rect_start, extent=rect_extent, shape=img.shape)
img[rr, cc] = wheel_color


#---------------------------------------------
# Write a bunch of information on the wheel.
#---------------------------------------------
labels = []
labels.append ( f"wheel of: {vehicle_name}" )
labels.append (  "   " )
labels.append ( f"vehicle mass: {mass_of_vehicle} kg" )
labels.append (  "   " )
labels.append ( f"force on wheel: {force_per_wheel} N" )
labels.append (  "   " )
labels.append ( f"sinks to {total_compression:.2f} cm" )

x       = first_layer_left_edge + 20
y       = 30
spacing = 30
for i in range(len(labels)) :
  mpl.text ( x,  y, labels[i],  color=white )
  y += spacing


#--------------------------------
# Save out the image
#--------------------------------
filename = './image.png'
mpl.imshow ( img )
mpl.axis ( 'off' )
mpl.savefig ( filename, bbox_inches='tight', dpi=400 )

print ( f"\n\nWrote image to {filename}\n\n" )


