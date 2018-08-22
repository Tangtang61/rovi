import numpy as np
import math
from geometry_msgs.msg import Transform

def dict2tf(d):
  tf=Transform()
  tf.translation.x=d['translation']['x']
  tf.translation.y=d['translation']['y']
  tf.translation.z=d['translation']['z']
  tf.rotation.x=d['rotation']['x']
  tf.rotation.y=d['rotation']['y']
  tf.rotation.z=d['rotation']['z']
  tf.rotation.w=d['rotation']['w']
  return tf

def toRT(tf):
  x=tf.rotation.x
  y=tf.rotation.y
  z=tf.rotation.z
  w=tf.rotation.w
  tx=tf.translation.x
  ty=tf.translation.y
  tz=tf.translation.z
  xx=x*x
  yy=y*y
  zz=z*z
  ww=w*w
  return np.matrix([[xx-yy-zz+ww,2.*(x*y-w*z),2.*(x*z+w*y),tx],[2.*(x*y+w*z),yy+ww-xx-zz,2.*(y*z-w*x),ty],[2.*(x*z-w*y),2.*(y*z+w*x),zz+ww-xx-yy,tz],[ 0, 0, 0, 1]])

def fromRT(rt):
  qw=2*math.sqrt(1+rt[0,0]+rt[1,1]+rt[2,2])
  qx=(rt[2,1]-rt[1,2])/qw
  qy=(rt[0,2]-rt[2,0])/qw
  qz=(rt[1,0]-rt[0,1])/qw
  tf=Transform()
  tf.rotation.w=qw
  tf.rotation.x=qx
  tf.rotation.y=qy
  tf.rotation.z=qz
  tf.rotation.x=rt[0,3]
  tf.rotation.y=rt[1,3]
  tf.rotation.z=rt[2,3]
  return tf

def inv(tf):
  ft=Transform()
  ft.translation.x=-tf.translation.x
  ft.translation.y=-tf.translation.y
  ft.translation.z=-tf.translation.z
  ft.rotation.x=-tf.rotation.x
  ft.rotation.y=-tf.rotation.y
  ft.rotation.z=-tf.rotation.z
  ft.rotation.w=tf.rotation.w
  return ft
